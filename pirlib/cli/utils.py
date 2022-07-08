import argparse
import importlib
from typing import List, Optional

from pirlib.backends import Backend
from pirlib.pipeline import PipelineDefinition
from pirlib.pir import Package


def pipeline_def(arg: str) -> PipelineDefinition:
    if arg.count(":") != 1:
        raise argparse.ArgumentTypeError(
            f"malformatted reference to pipeline definition '{arg}'"
        )
    module_name, pipeline_name = arg.split(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as err:
        raise argparse.ArgumentTypeError(f"{err}")
    try:
        pipeline = getattr(module, pipeline_name)
    except AttributeError as err:
        raise argparse.ArgumentTypeError(f"{err}")
    if not isinstance(pipeline, PipelineDefinition):
        raise argparse.ArgumentTypeError(f"{arg} has unexpected type {type(pipeline)}")
    return pipeline


def package_pipelines(
    parser: argparse.ArgumentParser,
    pipelines: List[PipelineDefinition],
    flatten: Optional[bool] = False,
) -> Package:
    package = Package(graphs={})
    for pipeline in pipelines:
        pkg = pipeline.package()
        if flatten:
            graph_id = pipeline.name
            pkg.graphs = {
                pipeline.name: pkg.flatten_graph(graph_id, validate=True)
            }
        for g_id, g in pkg.graphs.items():
            if g_id in package.graphs:
                if g != package.graphs.get(g_id):
                    parser.error(f"conflicting graphs id '{g_id}'")
                continue
            else:
                package.add_graph(g)
    return package
