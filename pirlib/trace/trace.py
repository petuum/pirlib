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
from pirlib.graph import (DataSource, Entrypoint, Graph, GraphInput,
                          GraphOutput, Node, NodeInput, NodeOutput,
                          DataSource, Package, Subgraph, find_by_name)

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
        return {k: recurse_hint(func, f"{prefix}.{k}", h,
                                *(val[k] for val in values))
                for k, h in hint.__annotations__.items()}
    if typing.get_origin(hint) is tuple:
        return tuple(recurse_hint(func, f"{prefix}.{k}", h,
                                  *(val[k] for val in values))
                     for k, h in enumerate(typing.get_args(hint)))
    return func(prefix, hint, *values)


def iter_hints(prefix, hint, *values):
    hints = []
    recurse_hint(lambda *args: hints.append(args), prefix, hint, *values)
    return iter(hints)


def package_operator(func: callable, name: str, config: dict) -> Package:
    graph = Graph(name=name, nodes=[], inputs=[], outputs=[])
    package = Package(graphs=[graph])
    package.graphs.append(graph)
    sig = inspect.signature(func)
    input_types = _flatten_param_types(func)
    for name, pytype in input_types.items():
        iotype = pytype_to_iotype(pytype)
        source = DataSource(graph_input=name)
        graph.inputs.append(GraphInput(name=name, iotype=iotype))
    ivalues = func(**kwargs)
    output_types = _flatten_return_type(func)
    if typing.get_origin(sig.return_annotation) == tuple:
        pytypes = typing.get_args(sig.return_annotation)
    else:
        pytypes = [sig.return_annotation]
        ivalues = [ivalues]
    for idx, (iv, pytype) in enumerate(zip(ivalues, pytypes)):
        iotype = pytype_to_iotype(pytype)
        graph.outputs.append(GraphOutput(name=f"{idx}", iotype=iotype,
                                         source=iv.source))


def package_pipeline(func: callable, name: str, config: dict) -> Package:
    if is_packaging():
        raise RuntimeError("packaging already in process")
    package = Package(graphs=[])
    token = _PACKAGE.set(package)
    try:
        _pipeline_to_graph(func, name, config)
        package.validate()
        return package
    finally:
        _PACKAGE.reset(token)


def _pipeline_to_graph(pipeline_func: callable,
                       pipeline_name: str,
                       pipeline_config: dict) -> Graph:
    sig = inspect.signature(pipeline_func)
    graph = Graph(name=pipeline_name, nodes=[], subgraphs=[],
                  inputs=[], outputs=[])
    token = _GRAPH.set(graph)

    def add_input(name, hint):
        iotype = pytype_to_iotype(hint)
        source = DataSource(graph_input=name)
        graph.inputs.append(GraphInput(name=name, iotype=iotype))
        return _create_ivalue(pytype=hint, source=source)

    try:
        args, kwargs = [], {}
        for param in sig.parameters.values():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                raise ValueError("{} not supported".format(param))
            input_ivalue = recurse_hint(add_input, param.name,
                                        param.annotation)
            if param.kind == param.KEYWORD_ONLY:
                kwargs[param.name] = input_ivalue
            else:
                args.append(input_ivalue)
        return_ivalue = pipeline_func(*args, **kwargs)
        flat_outputs = iter_hints(
            "return", sig.return_annotation, return_ivalue)
        for name, hint, ivalue in flat_outputs:
            iotype = pytype_to_iotype(ivalue.pytype)
            graph.outputs.append(GraphOutput(name=name, iotype=iotype,
                                             source=ivalue.source))
        package = _PACKAGE.get()
        assert find_by_name(package.graphs, graph.name) is None
        package.graphs.append(graph)
        return graph
    finally:
        _GRAPH.reset(token)


def pipeline_call(method):

    @functools.wraps(method)
    def wrapper(instance, *args, **kwargs):
        if not is_packaging():
            return method(instance, *args, **kwargs)
        graph = _GRAPH.get()
        g = _pipeline_to_graph(
            pipeline_func=instance.func,
            pipeline_name=instance.name,
            pipeline_config=instance.config,
        )
        subgraph = Subgraph(
            name=instance.name, 
            graph=g.name,
            config=instance.config,
            inputs=[],
            outputs=[],
        )
        sig = inspect.signature(instance.func)
        for idx, param in enumerate(sig.parameters.values()):
            value = args[idx] if idx < len(args) else kwargs[param.name]
            for n, h, v in iter_hints(param.name, param.annotation, value):
                iotype = pytype_to_iotype(h)
                subgraph.inputs.append(
                    NodeInput(name=n, iotype=iotype, source=v.source))

        def return_value(name, hint):
            iotype = pytype_to_iotype(hint)
            source = DataSource(subgraph=subgraph.name, output=name)
            subgraph.outputs.append(NodeOutput(name=name, iotype=iotype))
            return _create_ivalue(pytype=hint, source=source)
        value = recurse_hint(return_value, "return", sig.return_annotation)
        graph.subgraphs.append(subgraph)
        return value
    return wrapper


def _add_node_input(node, name, hint, ivalue):
    iotype = pytype_to_iotype(hint)
    node.inputs.append(NodeInput(name=name, iotype=iotype,
                                 source=ivalue.source))


def _add_node_output(node, name, hint):
    source = DataSource(node=node.name, output=name)
    iotype = pytype_to_iotype(hint)
    node.outputs.append(NodeOutput(name=name, iotype=iotype))
    return _create_ivalue(pytype=hint, source=source)


def _create_node_template(instance, inputs=None, outputs=None):
    return Node(
        name=instance.name,
        config=instance.config,
        inputs=[] if inputs is None else inputs,
        outputs=[] if outputs is None else outputs,
        entrypoint=Entrypoint(
            version="v1",
            handler=f"{instance.func.__module__}:{instance.func.__name__}",
            runtime=f"python:{sys.version_info[0]}.{sys.version_info[1]}",
        ),
        framework=instance.framework,
    )


def operator_call(func):

    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        if not is_packaging():
            return func(instance, *args, **kwargs)
        graph = _GRAPH.get()
        if instance.name in [node.name for node in graph.nodes]:
            raise ValueError(f"pipeline already contains node {nodename}")
        node = _create_node_template(instance)
        graph.nodes.append(node)
        sig = inspect.signature(instance.func)
        for idx, (name, param) in enumerate(sig.parameters.items()):
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                raise ValueError("{} not supported".format(param))
            ivalue = args[idx] if idx < len(args) else kwargs[name]
            recurse_hint(functools.partial(_add_node_input, node),
                         param.name, param.annotation, ivalue)
        return recurse_hint(functools.partial(_add_node_output, node),
                            "return", sig.return_annotation)
    return wrapper
