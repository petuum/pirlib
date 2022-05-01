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
    package = Package(graphs=[])
    for pipeline in pipelines:
        pkg = pipeline.package()
        if flatten:
            pkg.graphs = [pkg.flatten_graph(pipeline.name, validate=True)]
        for g in pkg.graphs:
            for graph in package.graphs:
                if g.name == graph.name:
                    if g != graph:
                        parser.error(f"conflicting graphs named '{g.name}'")
                    break
            else:
                package.graphs.append(g)
    return package
