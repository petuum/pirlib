import argparse
import base64
import dataclasses
import json
import pickle
import sys
import yaml
from typing import Optional

import pirlib.graph
from pirlib.backends import Backend


def encode(x):
    return base64.b64encode(pickle.dumps(x)).decode()


def decode(x):
    return pickle.loads(base64.b64decode(x.encode()))


class DockerBatchBackend(Backend):

    def execute_parser(self):
        pass

    def execute(self):
        pass

    def generate_parser(self):
        pass

    def generate(
            self,
            package: pirlib.graph.Package,
            config: Optional[dict] = None,
            args: Optional[argparse.Namespace] = None,
        ) -> None:
        compose = {
            "version": "3.9",
            "services": {},
            "volumes": {"node_outputs": {}},
        }
        assert len(package.graphs) == 1
        graph = package.graphs[0]  # FIXME: need to handle multiple graphs
        for node in graph.nodes:
            service = compose["services"][f"{graph.name}.{node.name}"] = {
                "image": node.entrypoint.image,
                "command": ["python", "-m", __name__, "node",
                            encode(node), encode(graph.inputs)],
                "volumes": ["node_outputs:/mnt/node_outputs"],
            }
            for inp in node.inputs:
                if inp.source.node_output is not None:
                    name = f"{graph.name}.{inp.source.node_output.node_name}"
                    service.setdefault("depends_on", {})[name] = {
                        "condition": "service_completed_successfully",
                    }
                if inp.source.graph_input is not None:
                    name = inp.source.graph_input
                    path = f"${{INPUT_{name}:?err}}"
                    service["volumes"].append(
                        f"{path}:/mnt/graph_inputs/{name}")
        service = compose["services"][f"{graph.name}"] = {
            "image": node.entrypoint.image,  # FIXME: a bit of a hack.
            "command": ["python", "-m", __name__, "graph",
                        encode(graph.outputs)],
            "volumes": ["node_outputs:/mnt/node_outputs"],
        }
        for g_inp in graph.inputs:
            path = f"${{INPUT_{g_inp.name}:?err}}"
            service["volumes"].append(f"{path}:/mnt/graph_inputs/{g_inp.name}")
        if graph.outputs:
            service["volumes"].append(f"${{OUTPUT:?err}}:/mnt/graph_outputs")
        service["depends_on"] = {}
        for node in graph.nodes:
            service["depends_on"][f"{graph.name}.{node.name}"] = {
                "condition": "service_completed_successfully",
            }
        if args is not None and args.output is not None:
            with open(args.output, "w") as f:
                yaml.dump(compose, f)
        return compose


def run_node(node, graph_inputs):
    import importlib
    import pandas
    import pathlib
    from pirlib.iotypes import DirectoryPath, FilePath
    module_name, handler_name = node.entrypoint.handler.split(":")
    handler = getattr(importlib.import_module(module_name), handler_name)
    inputs = {}
    for inp in node.inputs:
        if inp.source.node_output is not None:
            ref = inp.source.node_output
            path = f"/mnt/node_outputs/{ref.node_name}/{ref.output_name}"
        if inp.source.graph_input is not None:
            path = f"/mnt/graph_inputs/{inp.source.graph_input}"
        if inp.iotype == "DIRECTORY":
            inputs[inp.name] = DirectoryPath(path)
        elif inp.iotype == "FILE":
            inputs[inp.name] = FilePath(path)
        elif inp.iotype == "DATAFRAME":
            inputs[inp.name] = pandas.read_csv(path)
        else:
            raise TypeError(f"unsupported iotype {inp.iotype}")
    outputs = {}
    for out in node.outputs:
        path = f"/mnt/node_outputs/{node.name}/{out.name}"
        if out.iotype == "DIRECTORY":
            outputs[out.name] = DirectoryPath(path)
            outputs[out.name].mkdir(parents=True, exist_ok=True)
        elif out.iotype == "FILE":
            outputs[out.name] = FilePath(path)
            outputs[out.name].parents[0].mkdir(parents=True, exist_ok=True)
        else:
            outputs[out.name] = None
    handler.run_handler(node, inputs, outputs)
    for out in node.outputs:
        path = f"/mnt/node_outputs/{node.name}/{out.name}"
        if out.iotype == "DATAFRAME":
            pathlib.Path(path).parents[0].mkdir(parents=True, exist_ok=True)
            outputs[out.name].to_csv(path)


def run_graph(graph_outputs):
    import shutil
    for g_out in graph_outputs:
        if g_out.source.node_output is not None:
            ref = g_out.source.node_output
            path_from = f"/mnt/node_outputs/{ref.node_name}/{ref.output_name}"
        if g_out.source.graph_input is not None:
            path_from = f"/mnt/graph_inputs/{g_out.source.graph_input}"
        path_to = f"/mnt/graph_outputs/{g_out.name}"
        if g_out.iotype == "DIRECTORY":
            shutil.coptytree(path_from, path_to)
        else:
            shutil.copy(path_from, path_to)


if __name__ == "__main__":
    if sys.argv[1] == "node":
        node = decode(sys.argv[2])
        graph_inputs = decode(sys.argv[3])
        run_node(node, graph_inputs)
    else:
        assert sys.argv[1] == "graph"
        graph_outputs = decode(sys.argv[2])
        run_graph(graph_outputs)
