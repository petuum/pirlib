import contextvars
import copy
import functools
import inspect
import sys
import threading
import typing

from dataclasses import dataclass
from typing import Optional

from pirlib.iotypes import pytype_to_iotype
from pirlib.graph import (DataSource, Entrypoint, Graph, GraphInput,
                          GraphOutput, Node, NodeInput, NodeOutput,
                          DataSource, NodeOutputRef, Package)

_PACKAGE = contextvars.ContextVar("_PACKAGE")


@dataclass
class IntermediateValue:
    pytype: type
    source: DataSource


def is_packaging():
    return _PACKAGE.get(None) is not None


def package_operator(func: callable, name: str, config: dict) -> Package:
    
    if is_packaging():
        raise RuntimeError("packaging already in process")
    package = Package(graphs=[])
    token = _PACKAGE.set(package)
    try:
        _pipeline_to_graph(func, name, config)
        return package
    finally:
        _PACKAGE.reset(token)


def package_pipeline(func: callable, name: str, config: dict) -> Package:
    if is_packaging():
        raise RuntimeError("packaging already in process")
    package = Package(graphs=[])
    token = _PACKAGE.set(package)
    try:
        _pipeline_to_graph(func, name, config)
        return package
    finally:
        _PACKAGE.reset(token)


def _pipeline_to_graph(func: callable, name: str, config: dict) -> Graph:
    graph = Graph(name=name, nodes=[], inputs=[], outputs=[])
    package = _PACKAGE.get()
    package.graphs.append(graph)
    sig = inspect.signature(func)
    args = []
    kwargs = {}
    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise ValueError("{} not supported".format(param))
        source = DataSource(graph_input=name)
        ivalue = IntermediateValue(pytype=param.annotation, source=source)
        if param.kind == param.KEYWORD_ONLY:
            kwargs[param.name] = ivalue
        else:
            args.append(ivalue)
        iotype = pytype_to_iotype(ivalue.pytype)
        graph.inputs.append(GraphInput(name=name, iotype=iotype))
    ivalues = func(*args, **kwargs)
    if typing.get_origin(sig.return_annotation) == tuple:
        pytypes = typing.get_args(sig.return_annotation)
    else:
        pytypes = [sig.return_annotation]
        ivalues = [ivalues]
    for idx, (iv, pytype) in enumerate(zip(ivalues, pytypes)):
        assert isinstance(iv, IntermediateValue)
        iotype = pytype_to_iotype(pytype)
        graph.outputs.append(GraphOutput(name=f"{idx}", iotype=iotype,
                                         source=iv.source))


def pipeline_call(method):

    @functools.wraps(method)
    def wrapper(instance, *args, **kwargs):
        if not is_packaging():
            return method(instance, *args, **kwargs)
        _pipeline_to_graph(
            func=instance.func,
            name=instance.name,
            config=instance.config,
        )
        subgraph = _PACKAGE.get().graphs.pop()
        graph = _PACKAGE.get().graphs[-1]
        # Flatten-merge the subgraph into the current graph.
        input_map = {}  # GraphInput.name -> IntermediateValue
        sig = inspect.signature(instance.func)
        for idx, (name, param) in enumerate(sig.parameters.items()):
            input_map[name] = args[idx] if idx < len(args) else kwargs[name]
        for node in subgraph.nodes:
            node.name = f"{subgraph.name}.{node.name}"
            for inp in node.inputs:
                source = inp.source
                if source.node_output is not None:
                    ref = source.node_output
                    ref.node_name = f"{subgraph.name}.{ref.node_name}"
                if source.graph_input is not None:
                    inp.source = input_map[source.graph_input].source
            graph.nodes.append(node)
        # Create intermediate values for subgraph outputs.
        ivalues = []
        return_type = typing.get_origin(sig.return_annotation)
        if return_type == tuple:
            pytypes = typing.get_args(sig.return_annotation)
        else:
            pytypes = [sig.return_annotation]
        for idx, (out, pytype) in enumerate(zip(subgraph.outputs, pytypes)):
            assert out.name == f"{idx}"
            source = out.source
            if source.node_output is not None:
                ref = source.node_output
                ref.node_name = f"{subgraph.name}.{ref.node_name}"
            if source.graph_input is not None:
                source = input_map[source.graph_input].source
            ivalues.append(IntermediateValue(pytype=pytype, source=source))
        if return_type == tuple:
            return tuple(ivalues)
        return ivalues[0]
    return wrapper


def operator_call(func):

    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        if not is_packaging():
            return func(instance, *args, **kwargs)
        graph = _PACKAGE.get().graphs[-1]
        nodename = instance.name
        if nodename in [node.name for node in graph.nodes]:
            raise ValueError(f"pipeline already contains node {nodename}")
        sig = inspect.signature(instance.func)
        # Create new intermediate values from return annotation.
        ivalues = []
        return_type = typing.get_origin(sig.return_annotation)
        if return_type == tuple:
            pytypes = typing.get_args(sig.return_annotation)
        else:
            pytypes = [sig.return_annotation]
        for idx, pytype in enumerate(pytypes):
            ref = NodeOutputRef(node_name=nodename, output_name=f"{idx}")
            source = DataSource(node_output=ref)
            ivalues.append(IntermediateValue(pytype=pytype, source=source))
        # Convert intermediate values to outputs.
        outputs = [NodeOutput(name=iv.source.node_output.output_name,
                              iotype=pytype_to_iotype(iv.pytype))
                   for idx, iv in enumerate(ivalues)]
        # Create a new node in the graph.
        node = Node(
            name=nodename,
            config=instance.config,
            inputs=_extract_node_inputs(instance.func, nodename, *args, **kwargs),
            outputs=outputs,
            entrypoint=Entrypoint(
                version="v1",
                handler=f"{instance.func.__module__}:{instance.func.__name__}",
                runtime=f"python:{sys.version_info[0]}.{sys.version_info[1]}",
            ),
            framework=instance.framework,
        )
        # Add the new node to the graph.
        graph.nodes.append(node)
        if return_type == tuple:
            return tuple(ivalues)
        return ivalues[0]
    return wrapper


def _extract_node_inputs(function, nodename, *args, **kwargs):
    sig = inspect.signature(function)
    node_inputs = []
    for idx, (name, param) in enumerate(sig.parameters.items()):
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise ValueError("{} not supported".format(param))
        value = args[idx] if idx < len(args) else kwargs.pop(name)
        assert isinstance(value, IntermediateValue)
        iotype = pytype_to_iotype(param.annotation)
        node_inputs.append(NodeInput(name=name, iotype=iotype,
                                     source=value.source))
    return node_inputs
