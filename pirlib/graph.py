import copy
import re
import typeguard
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ValidationError(ValueError):

    def __init__(self, message):
        super().__init__(message)


def _validate_fields(instance):
    classname = instance.__class__.__name__
    for name, hint in instance.__annotations__.items():
        value = getattr(instance, name)
        try:
            typeguard.check_type(f"{classname}.{name}", value, hint)
        except TypeError as err:
            raise ValidationError(err.message) from None


def _validate_names(items: Any, label: str) -> None:
    once = set()
    twice = set()
    for item in items:
        if item.name not in once:
            once.add(item.name)
        else:
            twice.add(item.name)
    if twice:
        text = ", ".join(repr(name) for name in twice)
        raise ValidationError(f"duplicate {label} name(s): {text}")


def find_by_name(iterable, name):
    for item in iterable:
        if item.name == name:
            return item


@dataclass
class DataSource:
    node: Optional[str] = None
    subgraph: Optional[str] = None
    output: Optional[str] = None
    graph_input: Optional[str] = None

    def validate(self):
        _validate_fields(self)
        count = sum([
            self.node is not None,
            self.subgraph is not None,
            self.graph_input is not None,
        ])
        if count != 1:
            raise ValidationError("exactly one of 'node', 'subgraph', "
                                  "or 'graph_input' is expected")
        if self.node is not None or self.subgraph is not None:
            if self.output is None:
                raise ValidationError("'output' is required if either "
                                      "'node' or 'subgraph' is provided")


@dataclass
class Input:
    name: str
    iotype: str
    source: DataSource

    def validate(self):
        _validate_fields(self)
        try:
            self.source.validate()
        except ValidationError as err:
            raise ValidationError(f"source: {err}") from None


@dataclass
class Output:
    name: str
    iotype: str

    def validate(self):
        _validate_fields(self)


@dataclass
class Framework:
    name: str
    config: Dict[str, Any] = field(default_factory=dict)

    def validate(self):
        _validate_fields(self)


@dataclass
class Entrypoint:
    version: str
    handler: str
    runtime: str
    codeuri: Optional[str] = None
    image: Optional[str] = None

    def validate(self):
        _validate_fields(self)
        # Format: (relative/path/from/codeuri/)(package.module):(name)
        pattern = re.compile(r"^(.*/)?([^:]*):([^:]*)$")
        if pattern is None:
            raise ValidationError(f"malformed handler '{self.handler}'")


@dataclass
class Node:
    name: str
    entrypoint: Entrypoint
    framework: Optional[Framework] = None
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[Input] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)

    def validate(self):
        _validate_fields(self)
        for inp in self.inputs:
            try:
                inp.validate()
            except ValidationError as err:
                raise ValidationError(f"input '{inp.name}': {err}") from None
        _validate_names(self.inputs, "input")
        for out in self.outputs:
            try:
                out.validate()
            except ValidationError as err:
                raise ValidationError(f"output '{out.name}': {err}") from None
        _validate_names(self.outputs, "output")
        try:
            self.entrypoint.validate()
        except ValidationError as err:
            raise ValidationError(f"entrypoint: {err}") from None
        if self.framework is not None:
            try:
                self.framework.validate()
            except ValidationError as err:
                raise ValidationError(f"framework: {err}") from None


@dataclass
class Subgraph:
    name: str
    graph: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[Input] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)

    def validate(self):
        _validate_fields(self)
        for inp in self.inputs:
            try:
                inp.validate()
            except ValidationError as err:
                raise ValidationError(f"input '{inp.name}': {err}") from None
        _validate_names(self.inputs, "input")
        for out in self.outputs:
            try:
                out.validate()
            except ValidationError as err:
                raise ValidationError(f"output '{out.name}': {err}") from None
        _validate_names(self.outputs, "output")


@dataclass
class GraphInput:
    name: str
    iotype: str

    def validate(self):
        _validate_fields(self)


@dataclass
class GraphOutput:
    name: str
    iotype: str
    source: DataSource

    def validate(self):
        _validate_fields(self)
        self.source.validate()


@dataclass
class Graph:
    name: str
    nodes: List[Node] = field(default_factory=list)
    subgraphs: List[Subgraph] = field(default_factory=list)
    inputs: List[GraphInput] = field(default_factory=list)
    outputs: List[GraphOutput] = field(default_factory=list)

    def validate(self):
        _validate_fields(self)
        for node in self.nodes:
            try:
                node.validate()
            except ValidationError as err:
                raise ValidationError(f"node '{node.name}': {err}") from None
        _validate_names(self.nodes, "node")
        for subgraph in self.subgraphs:
            try:
                subgraph.validate()
            except ValidationError as err:
                raise ValidationError(
                    f"subgraph '{subgraph.name}': {err}") from None
        _validate_names(self.subgraphs, "subgraph")
        for inp in self.inputs:
            try:
                inp.validate()
            except ValidationError as err:
                raise ValidationError(
                    f"graph input '{inp.name}': {err}") from None
        _validate_names(self.inputs, "graph input")
        for out in self.outputs:
            try:
                out.validate()
            except ValidationError as err:
                raise ValidationError(
                    f"graph output '{out.name}': {err}") from None
        _validate_names(self.outputs, "graph output")
        self._validate_connectivity()
        self._validate_acyclicity()

    def _validate_connectivity(self):
        for out in self.outputs:
            try:
                self._validate_source(out.source, out.iotype)
            except ValidationError as err:
                raise ValidationError(
                    f"graph output '{out.name}': {err}") from None
        for node in self.nodes:
            for inp in node.inputs:
                try:
                    self._validate_source(inp.source, inp.iotype)
                except ValidationError as err:
                    raise ValidationError(f"node '{node.name}': input "
                                          f"'{inp.name}': {err}") from None

    def _validate_source(self, source, iotype):
        if source.graph_input is not None:
            graph_input = find_by_name(self.inputs, source.graph_input)
            if graph_input is None:
                raise ValidationError(f"reference to missing graph "
                                      f"input '{source.graph_input}'")
            source_iotype = graph_input.iotype
        elif source.node is not None:
            node = find_by_name(self.nodes, source.node)
            if node is None:
                raise ValidationError(
                    f"reference to missing node '{source.node}'")
            output = find_by_name(node.outputs, source.output)
            if output is None:
                raise ValidationError(f"reference to missing output "
                                      f"'{source.output}' of node "
                                      f"'{node.name}'")
            source_iotype = output.iotype
        elif source.subgraph is not None:
            subgraph = find_by_name(self.subgraphs, source.subgraph)
            if subgraph is None:
                raise ValidationError(
                    f"reference to missing subgraph '{source.subgraph}'")
            output = find_by_name(subgraph.outputs, source.output)
            if output is None:
                raise ValidationError(f"reference to missing output "
                                      f"'{source.output}' of subgraph "
                                      f"'{subgraph.name}'")
            source_iotype = output.iotype
        if source_iotype != iotype:
            raise ValidationError(f"iotype '{iotype}' differs from "
                                  f"source iotype '{source_iotype}'")

    def _validate_acyclicity(self):
        visited_node_names = set()
        visited_subgraph_names = set()
        for root in self.nodes + self.subgraphs:
            stack = [root]
            while stack:
                item = stack.pop()
                if isinstance(item, Node):
                    if item.name in visited_node_names:
                        continue
                    visited_node_names.add(item.name)
                elif isinstance(item, Subgraph):
                    if item.name in visited_subgraph_names:
                        continue
                    visited_subgraph_names.add(item.name)
                for inp in item.inputs:
                    if inp.source.node is not None:
                        name = inp.source.node
                        node = find_by_name(self.nodes, name)
                        if node == root:
                            raise ValidationError(
                                f"cycle detected containing node '{name}'")
                        stack.append(node)
                    elif inp.source.subgraph is not None:
                        name = inp.source.subgraph
                        subgraph = find_by_name(self.subgraphs, name)
                        if subgraph == root:
                            raise ValidationError(
                                f"cycle detected containing subgraph '{name}'")
                        stack.append(subgraph)


@dataclass
class Package:
    graphs: List[Graph] = field(default_factory=list)

    def flatten_graph(self, graph_name, validate=False):
        # TODO: error checking
        graph = copy.deepcopy(find_by_name(self.graphs, graph_name))
        for subgraph in graph.subgraphs:
            g = self.flatten_graph(subgraph.graph)
            # Add prefix to subgraph nodes names.
            for n in g.nodes:
                n.name = f"{subgraph.name}.{n.name}"
                for i in n.inputs:
                    if i.source.node is not None:
                        i.source.node = f"{subgraph.name}.{i.source.node}"
            for o in g.outputs:
                if o.source.node is not None:
                    o.source.node = f"{subgraph.name}.{o.source.node}"
            # Merge subgraph into main graph.
            for node in graph.nodes:
                for inp in node.inputs:
                    if inp.source.subgraph == subgraph.name:
                        for o in g.outputs:
                            if o.name == inp.source.output:
                                inp.source = o.source
            for out in graph.outputs:
                if out.source.subgraph == subgraph.name:
                    for o in g.outputs:
                        if o.name == out.source.output:
                            out.source = o.source
            for n in g.nodes:
                for i in n.inputs:
                    if i.source.graph_input is not None:
                        for si in subgraph.inputs:
                            if i.source.graph_input == si.name:
                                i.source = si.source
            graph.nodes.extend(g.nodes)
        graph.subgraphs = []
        graph.validate()
        return graph

    def validate(self):
        _validate_names(self.graphs, "graph")
        for graph in self.graphs:
            try:
                graph.validate()
            except ValidationError as err:
                raise ValidationError(f"graph '{graph.name}': {err}") from None
            for subgraph in graph.subgraphs:
                self._validate_subgraph(subgraph)
        # TODO: check for infinitely nested subgraphs

    def _validate_subgraph(self, subgraph):
        graph = find_by_name(self.graphs, subgraph.graph)
        if graph is None:
            raise ValidationError(f"subgraph '{subgraph.name}': reference "
                                  f"to missing graph '{subgraph.graph}'")
        # TODO: check subgraph inputs and outputs match graph inputs and outputs
