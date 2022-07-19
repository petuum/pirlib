import contextvars
import copy
import functools
import inspect
import sys
import threading
import typeguard
import typing
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from pirlib.iotypes import pytype_to_iotype
from pirlib.pir import (
    DataSource,
    Entrypoint,
    Graph,
    GraphInput,
    GraphOutput,
    Node,
    Input,
    Output,
    Package,
    Subgraph,
    find_by_id,
)

_PACKAGE = contextvars.ContextVar("_PACKAGE")
_GRAPH = contextvars.ContextVar("_GRAPH")


def _create_ivalue(pytype, source):
    class IntermediateValue:

        __module__ = pytype.__module__
        __qualname__ = pytype.__qualname__

        def __init__(self, pytype, source):
            self.pytype = pytype
            self.source = source

        @property
        def __class__(self):
            return self.pytype

    return IntermediateValue(pytype, source)


def is_packaging():
    return _PACKAGE.get(None) is not None


def _is_typeddict(hint):
    if sys.version_info < (3, 10):
        return isinstance(hint, typing._TypedDictMeta)
    return typing.is_typeddict(hint)


def recurse_hint(func, prefix, hint, *values):
    if _is_typeddict(hint):
        return {
            k: recurse_hint(func, f"{prefix}.{k}", h, *(val[k] for val in values))
            for k, h in hint.__annotations__.items()
        }
    if typing.get_origin(hint) is tuple:
        return tuple(
            recurse_hint(func, f"{prefix}.{k}", h, *(val[k] for val in values))
            for k, h in enumerate(typing.get_args(hint))
        )
    return func(prefix, hint, *values)


def _inspect_graph_inputs(func: callable):
    inputs = []

    def add_input(name, hint):
        iotype = pytype_to_iotype(hint)
        graph_input_id = name
        source = DataSource(graph_input_id=graph_input_id)
        graph_input = GraphInput(
            id=graph_input_id,
            iotype=iotype
        )
        graph_input.meta.name = name
        inputs.append(graph_input)
        return _create_ivalue(pytype=hint, source=source)

    sig = inspect.signature(func)
    args, kwargs = [], {}
    for param in sig.parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise ValueError("{} not supported".format(param))
        value = recurse_hint(add_input, param.name, param.annotation)
        if param.kind == param.KEYWORD_ONLY:
            kwargs[param.name] = value
        else:
            args.append(value)
    return inputs, args, kwargs


def _inspect_graph_outputs(func: callable, return_value: typing.Any):
    outputs = []

    def add_output(name, hint, value):
        iotype = pytype_to_iotype(value.pytype)
        graph_output_id = name
        graph_output = GraphOutput(
            id=graph_output_id,
            iotype = iotype,
            source=value.source
        )
        graph_output.meta.name = name
        outputs.append(graph_output)

    sig = inspect.signature(func)
    recurse_hint(add_output, "return", sig.return_annotation, return_value)
    return outputs


def package_task(definition) -> Package:
    graph_id = node_id = definition.name
    graph = Graph(id=graph_id)
    graph.meta.name = definition.name
    graph.inputs, args, kwargs = _inspect_graph_inputs(definition.func)
    node = Node(
        id=node_id,
        entrypoints=_create_entrypoints(definition.func),
        framework=definition.framework,
        config=definition.config,
        inputs=_inspect_inputs(definition.func, args, kwargs),
    )
    node.meta.name = definition.name
    node.outputs, value = _inspect_outputs(definition.func, node=node_id)
    graph.outputs = _inspect_graph_outputs(definition.func, value)
    graph.nodes.append(node)
    package = Package(graphs=[graph])
    package.validate()
    return package


def package_pipeline(definition) -> Package:
    if is_packaging():
        raise RuntimeError("packaging already in process")
    package = Package(graphs=[])
    token = _PACKAGE.set(package)
    try:
        _pipeline_to_graph(definition.func, definition.name, definition.config)
    finally:
        _PACKAGE.reset(token)
    package.validate()
    return package


def _pipeline_to_graph(
    pipeline_func: callable, pipeline_name: str, pipeline_config: dict
) -> Graph:
    package = _PACKAGE.get()
    graph_id = pipeline_name
    graph = Graph(id=graph_id)
    graph.meta.name = pipeline_name
    graph.inputs, args, kwargs = _inspect_graph_inputs(pipeline_func)
    token = _GRAPH.set(graph)
    try:
        return_value = pipeline_func(*args, **kwargs)
    finally:
        _GRAPH.reset(token)
    graph.outputs = _inspect_graph_outputs(pipeline_func, return_value)
    assert find_by_id(package.graphs, graph.id) is None
    package.graphs.append(graph)
    return graph


def pipeline_call(method):
    @functools.wraps(method)
    def wrapper(instance, *args, **kwargs):
        if not is_packaging():
            return method(instance, *args, **kwargs)
        graph = _GRAPH.get()
        g = _pipeline_to_graph(
            pipeline_func=instance.defn.func,
            pipeline_name=instance.defn.name,
            pipeline_config=instance.defn.config,
        )
        subgraph_id = instance.name
        subgraph = Subgraph(
            id=subgraph_id,
            graph_id=g.id,
            config=instance.config,
            inputs=_inspect_inputs(instance.func, args, kwargs),
        )
        subgraph.meta.name = instance.name
        subgraph.outputs, value = _inspect_outputs(
            instance.func, subgraph=subgraph_id
        )
        graph.subgraphs.append(subgraph)
        return value

    return wrapper


def _inspect_inputs(func: callable, args, kwargs):
    inputs = []

    def add_input(name, hint, value):
        iotype = pytype_to_iotype(hint)
        input_id = name
        inp = Input(
            id=input_id,
            iotype=iotype,
            source=value.source
        )
        inp.meta.name = name
        inputs.append(inp)

    sig = inspect.signature(func)
    for idx, (name, param) in enumerate(sig.parameters.items()):
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise ValueError("{} not supported".format(param))
        value = args[idx] if idx < len(args) else kwargs[name]
        recurse_hint(add_input, param.name, param.annotation, value)
    return inputs


def _inspect_outputs(func: callable, node=None, subgraph=None):
    assert (node is None) ^ (subgraph is None)
    outputs = []

    def add_output(name, hint):
        source = DataSource(node_id=node, subgraph_id=subgraph, output_id=name)
        iotype = pytype_to_iotype(hint)
        output_id = name
        output = Output(
            id=output_id,
            iotype=iotype
        )
        output.meta.name = name
        outputs.append(output)
        return _create_ivalue(pytype=hint, source=source)

    sig = inspect.signature(func)
    value = recurse_hint(add_output, "return", sig.return_annotation)
    return outputs, value


def _create_entrypoints(func):
    entrypoint =  Entrypoint(
        version="v1",
        handler=f"{func.__module__}:{func.__name__}",
        runtime=f"python:{sys.version_info[0]}.{sys.version_info[1]}",
    )
    return {"main": entrypoint}


def task_call(func):
    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        if not is_packaging():
            return func(instance, *args, **kwargs)
        graph = _GRAPH.get()
        if find_by_id(graph.nodes, instance.name) is not None:
            raise ValueError(f"pipeline already contains node {instance.name}")
        node_id = instance.name
        node = Node(
            id=node_id,
            entrypoints=_create_entrypoints(instance.func),
            framework=instance.framework,
            config=instance.config,
            inputs=_inspect_inputs(instance.func, args, kwargs),
        )
        node.meta.name = instance.name
        node.outputs, value = _inspect_outputs(instance.func, node=node_id)
        graph.nodes.append(node)
        return value

    return wrapper
