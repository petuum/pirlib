import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class NodeOutputRef:
    node_name: str
    output_name: str


@dataclass
class DataSource:
    node_output: Optional[NodeOutputRef] = None
    graph_input: Optional[str] = None

    def __post_init__(self):
        if not (self.node_output is None) ^ (self.graph_input is None):
            raise ValueError("exactly one of node_output "
                             "or graph_input is required")


@dataclass
class NodeInput:
    name: str
    iotype: str
    source: DataSource


@dataclass
class NodeOutput:
    name: str
    iotype: str


@dataclass
class Framework:
    name: str
    config: Dict[str, Any]


@dataclass
class Entrypoint:
    version: str
    handler: str
    runtime: str
    codeuri: Optional[str] = None
    image: Optional[str] = None

    def validate(self):
        # Format: (relative/path/from/codeuri/)(package.module):(name)
        pattern = re.compile(r"^(.*/)?([^:]*):([^:]*)$")
        if pattern is None:
            raise ValueError(f"malformed handler '{self.handler}'")


@dataclass
class Node:
    name: str
    config: Dict[str, Any]
    inputs: List[NodeInput]
    outputs: List[NodeOutput]
    entrypoint: Entrypoint
    framework: Optional[Framework] = None


@dataclass
class GraphInput:
    name: str
    iotype: str


@dataclass
class GraphOutput:
    name: str
    iotype: str
    source: DataSource


@dataclass
class Graph:
    name: str
    nodes: List[Node]
    inputs: List[GraphInput]
    outputs: List[GraphOutput]


@dataclass
class Package:
    graphs: List[Graph]
