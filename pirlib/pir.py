"""
.. image:: ../_static/img/pir-diagram.svg
"""

import copy
import re
import typeguard
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pirlib.utils import find_by_name


@dataclass
class DataSource:
    """
    This dataclass encodes a reference to the source of an intermediate value in a PIR
    graph. A source can either be (1) an output of a node in the graph, (2) an output
    of a subgraph of the graph, or (3) an input of the graph itself.

    :ivar node: Name of the node in the graph if the source is the output of that node,
            ``None`` otherwise.
    :ivar subgraph: Name of the subgraph in the graph if the source is the output of
            that subgraph, ``None`` otherwise.
    :ivar output: Name of the output of a node or subgraph if the source is the output
            of that node or subgraph, ``None`` otherwise.
    :ivar graph_input: Name of the input of the graph if the source is the input of the
            graph, ``None`` otherwise.
    """
    node: Optional[str] = None
    subgraph: Optional[str] = None
    output: Optional[str] = None
    graph_input: Optional[str] = None

    def validate(self):
        _validate_fields(self)
        count = sum(
            [
                self.node is not None,
                self.subgraph is not None,
                self.graph_input is not None,
            ]
        )
        if count != 1:
            raise ValidationError(
                "exactly one of 'node', 'subgraph', or 'graph_input' is expected"
            )
        if self.node is not None or self.subgraph is not None:
            if self.output is None:
                raise ValidationError(
                    "'output' is required if either 'node' or 'subgraph' is provided"
                )


@dataclass
class Input:
    """
    This dataclass encodes a named input of a node or subgraph with a connected source.
    If it is the input of a subgraph, then its name must be equal to a name of some
    graph input of that subgraph.

    :ivar name: Name of the input. Must be unique among all inputs in a valid node or
            subgraph.
    :ivar iotype: Expected type of the input. In a valid graph, must be equal to the
            iotype of the source.
    :ivar source: Source of the input. Can be a graph input or a node/subgraph output.
    """
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
    """
    This dataclass encodes a named output of a node or a subgraph. An output can be an
    input source for other downstream nodes or subgraphs within the same graph, or be
    an output of the graph itself.

    :ivar name: Name of the output. Must be unique among all outputs in a valid node or
            subgraph.
    :ivar iotype: Type of the output.
    """
    name: str
    iotype: str

    def validate(self):
        _validate_fields(self)


@dataclass
class Framework:
    """
    This dataclass encodes the execution framework and configuration for a node.

    :ivar name: Name of the framework used for executing a node.
    :ivar config: Framework configuration for executing a node.
    """
    name: str
    config: Dict[str, Any] = field(default_factory=dict)

    def validate(self):
        _validate_fields(self)


@dataclass
class Entrypoint:
    """
    This dataclass encodes the entrypoint for executing a node. An entrypoint is
    typically a reference to a function or procedure in code (called "handler").

    :ivar version: The API version for the handler.
    :ivar handler: Reference to the handler, format depends on the runtime. For python
            runtimes, expects ``<module>.<name>``, where ``<module>`` is the fully
            qualified name of the module containing the handler, and ``<name>`` is the
            name of the handler object within that module.
    :ivar runtime: Identifier of the handler's runtime, e.g. ``"python:3.8"``.
    :ivar codeurl: Optional URL of the code used to run the handler. ``None`` means any
            and all handler code can be found in the local environment or docker image.
    :ivar image: Optional name of the Docker image used to run the handler. ``None``
            means the handler can be run in the local environment.
    """
    version: str
    handler: str
    runtime: str
    codeurl: Optional[str] = None
    image: Optional[str] = None

    def validate(self):
        _validate_fields(self)


@dataclass
class Node:
    """
    This dataclass encodes a node in a graph. A node represents a procedure that can be
    executed on several inputs to produce several outputs. All node inputs must have
    unique names, and all node outputs also must have unique names.

    :ivar name: Name of the node. Must be unique among all nodes in a valid graph.
    :ivar entrypoint: Entrypoint to the code executed by this node.
    :ivar framework: Execution framework for this node.
    :ivar config: Configuration values which are passed down to the procedure executed
            by this node. Can be any json or yaml serializable mapping.
    :ivar inputs: Expected inputs for this node, must all have unique names.
    :ivar outputs: Expected outputs for this node, must all have unique names.
    """
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
                raise ValidationError(f"subgraph '{subgraph.name}': {err}") from None
        _validate_names(self.subgraphs, "subgraph")
        for inp in self.inputs:
            try:
                inp.validate()
            except ValidationError as err:
                raise ValidationError(f"graph input '{inp.name}': {err}") from None
        _validate_names(self.inputs, "graph input")
        for out in self.outputs:
            try:
                out.validate()
            except ValidationError as err:
                raise ValidationError(f"graph output '{out.name}': {err}") from None
        _validate_names(self.outputs, "graph output")
        self._validate_connectivity()
        self._validate_acyclicity()

    def _validate_connectivity(self):
        for out in self.outputs:
            try:
                self._validate_source(out.source, out.iotype)
            except ValidationError as err:
                raise ValidationError(f"graph output '{out.name}': {err}") from None
        for node in self.nodes:
            for inp in node.inputs:
                try:
                    self._validate_source(inp.source, inp.iotype)
                except ValidationError as err:
                    raise ValidationError(
                        f"node '{node.name}': input '{inp.name}': {err}"
                    ) from None

    def _validate_source(self, source, iotype):
        if source.graph_input is not None:
            graph_input = find_by_name(self.inputs, source.graph_input)
            if graph_input is None:
                raise ValidationError(
                    f"reference to missing graph input '{source.graph_input}'"
                )
            source_iotype = graph_input.iotype
        elif source.node is not None:
            node = find_by_name(self.nodes, source.node)
            if node is None:
                raise ValidationError(f"reference to missing node '{source.node}'")
            output = find_by_name(node.outputs, source.output)
            if output is None:
                raise ValidationError(
                    f"reference to missing output '{source.output}' of node "
                    f"'{node.name}'"
                )
            source_iotype = output.iotype
        elif source.subgraph is not None:
            subgraph = find_by_name(self.subgraphs, source.subgraph)
            if subgraph is None:
                raise ValidationError(
                    f"reference to missing subgraph '{source.subgraph}'"
                )
            output = find_by_name(subgraph.outputs, source.output)
            if output is None:
                raise ValidationError(
                    f"reference to missing output '{source.output}' of subgraph "
                    f"'{subgraph.name}'"
                )
            source_iotype = output.iotype
        if source_iotype != iotype:
            raise ValidationError(
                f"iotype '{iotype}' differs from source iotype '{source_iotype}'"
            )

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
                                f"cycle detected containing node '{name}'"
                            )
                        stack.append(node)
                    elif inp.source.subgraph is not None:
                        name = inp.source.subgraph
                        subgraph = find_by_name(self.subgraphs, name)
                        if subgraph == root:
                            raise ValidationError(
                                f"cycle detected containing subgraph '{name}'"
                            )
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
            raise ValidationError(
                f"subgraph '{subgraph.name}': reference to missing graph "
                f"'{subgraph.graph}'"
            )
        # TODO: check subgraph inputs and outputs match graph inputs and outputs


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
