import re
import typeguard
from dataclasses import dataclass
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


@dataclass
class NodeOutputRef:
    node_name: str
    output_name: str

    def validate(self):
        _validate_fields(self)


@dataclass
class DataSource:
    node_output: Optional[NodeOutputRef] = None
    graph_input: Optional[str] = None

    def validate(self):  # TODO: merge NodeOutputRef
        _validate_fields(self)
        if not (self.node_output is None) ^ (self.graph_input is None):
            raise ValidationError("exactly one of node_output "
                                  "or graph_input is required")


@dataclass
class NodeInput:
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
class NodeOutput:
    name: str
    iotype: str

    def validate(self):
        _validate_fields(self)


@dataclass
class Framework:
    name: str
    config: Dict[str, Any]

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
    config: Dict[str, Any]
    inputs: List[NodeInput]
    outputs: List[NodeOutput]
    entrypoint: Entrypoint
    framework: Optional[Framework] = None

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
    nodes: List[Node]
    inputs: List[GraphInput]
    outputs: List[GraphOutput]

    def validate(self):
        _validate_fields(self)
        for node in self.nodes:
            try:
                node.validate()
            except ValidationError as err:
                raise ValidationError(f"node '{node.name}': {err}") from None
        _validate_names(self.nodes, "node")
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
            for graph_input in self.inputs:
                if graph_input.name == source.graph_input:
                    break
            else:
                raise ValidationError(f"reference to missing graph "
                                      f"input '{source.graph_input}'")
            source_iotype = graph_input.iotype
        elif source.node_output is not None:
            for node in self.nodes:
                if node.name == source.node_output.node_name:
                    break
            else:
                raise ValidationError(f"reference to missing node "
                                      f"'{source.node_output.node_name}'")
            ref = source.node_output
            for node_output in node.outputs:
                if node_output.name == ref.output_name:
                    break
            else:
                raise ValidationError(f"reference to missing output "
                                      f"'{ref.output_name}' of node "
                                      f"'{node.name}'")
            source_iotype = node_output.iotype
        if source_iotype != iotype:
            raise ValidationError(f"iotype '{iotype}' differs from "
                                  f"source iotype '{source_iotype}'")

    def _validate_acyclicity(self):
        visited_node_names = set()
        for root in self.nodes:
            stack = [root]
            while stack:
                item = stack.pop()
                if isinstance(item, Node):
                    if item.name in visited_node_names:
                        continue
                    visited_node_names.add(item.name)
                elif isinstance(item, Node):
                    pass  # TODO: consider subgraphs
                for inp in item.inputs:
                    if inp.source.node_output is not None:
                        name = inp.source.node_output.node_name
                        node = next(n for n in self.nodes if n.name == name)
                        if node == root:
                            raise ValidationError(
                                f"cycle detected containing node '{name}'")
                        stack.append(node)


@dataclass
class Package:
    graphs: List[Graph]

    def validate(self):
        _validate_names(self.graphs, "graph")
        for graph in self.graphs:
            try:
                graph.validate()
            except ValidationError as err:
                raise ValidationError(f"graph '{graph.name}': {err}") from None
