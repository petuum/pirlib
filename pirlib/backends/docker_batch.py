import argparse
import base64
import dataclasses
import json
import pickle
import sys
import yaml
from typing import Optional

import pirlib.pir
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
        package: pirlib.pir.Package,
        config: Optional[dict] = None,
        args: Optional[argparse.Namespace] = None,
    ) -> None:
        compose = {
            "version": "3.9",
            "services": {},
            "volumes": {"node_outputs": {}},
        }
        assert len(package.graphs) == 1
        graph_id, graph = list(package.graphs.items())[0]  # FIXME: need to handle multiple graphs
        for node_id, node in graph.nodes.items():
            service = compose["services"][f"{graph_id}.{node_id}"] = {
                "image": node.entrypoints["run"].env.image,
                "command": [
                    "python",
                    "-m",
                    __name__,
                    "node",
                    encode(node),
                    encode(graph.inputs),
                ],
                "volumes": ["node_outputs:/mnt/node_outputs"],
            }
            for inp in node.inputs.values():
                if inp.source.node_id is not None:
                    name = f"{graph_id}.{inp.source.node_id}"
                    service.setdefault("depends_on", {})[name] = {
                        "condition": "service_completed_successfully",
                    }
                if inp.source.graph_input_id is not None:
                    name = inp.source.graph_input_id
                    path = f"${{INPUT_{name}:?err}}"
                    service["volumes"].append(f"{path}:/mnt/graph_inputs/{name}")
        service = compose["services"][f"{graph_id}"] = {
            "image": node.entrypoints["run"].env.image,  # FIXME: a bit of a hack.
            "command": ["python", "-m", __name__, "graph", encode(graph.outputs)],
            "volumes": ["node_outputs:/mnt/node_outputs"],
        }
        for g_inp_id, g_inp in graph.inputs.items():
            path = f"${{INPUT_{g_inp_id}:?err}}"
            service["volumes"].append(f"{path}:/mnt/graph_inputs/{g_inp_id}")
        if graph.outputs:
            service["volumes"].append(f"${{OUTPUT:?err}}:/mnt/graph_outputs")
        service["depends_on"] = {}
        for node_id, node in graph.nodes.items():
            service["depends_on"][f"{graph_id}.{node_id}"] = {
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

    module_name, handler_name = node.entrypoints["run"].handler.split(":")
    handler = getattr(importlib.import_module(module_name), handler_name)
    inputs = {}
    for inp in node.inputs.values():
        if inp.source.node_id is not None:
            path = f"/mnt/node_outputs/{inp.source.node_id}/{inp.source.output_id}"
        if inp.source.graph_input_id is not None:
            path = f"/mnt/graph_inputs/{inp.source.graph_input}"
        if inp.meta.type == "DIRECTORY":
            inputs[inp.id] = DirectoryPath(path)
        elif inp.meta.type == "FILE":
            inputs[inp.id] = FilePath(path)
        elif inp.meta.type == "DATAFRAME":
            inputs[inp.id] = pandas.read_csv(path)
        else:
            raise TypeError(f"unsupported iotype {inp.meta.type}")
    outputs = {}
    for out in node.outputs.values():
        path = f"/mnt/node_outputs/{node.id}/{out.id}"
        if out.meta.type == "DIRECTORY":
            outputs[out.id] = DirectoryPath(path)
            outputs[out.id].mkdir(parents=True, exist_ok=True)
        elif out.meta.type == "FILE":
            outputs[out.id] = FilePath(path)
            outputs[out.id].parents[0].mkdir(parents=True, exist_ok=True)
        else:
            outputs[out.id] = None
    handler.run_handler(node, inputs, outputs)
    for out in node.outputs.values():
        path = f"/mnt/node_outputs/{node.id}/{out.id}"
        if out.meta.type == "DATAFRAME":
            pathlib.Path(path).parents[0].mkdir(parents=True, exist_ok=True)
            outputs[out.id].to_csv(path)


def run_graph(graph_outputs):
    import shutil

    for g_out in graph_outputs.values():
        source = g_out.source
        if source.node_id is not None:
            path_from = f"/mnt/node_outputs/{source.node_id}/{source.output_id}"
        if source.graph_input_id is not None:
            path_from = f"/mnt/graph_inputs/{source.graph_input_id}"
        path_to = f"/mnt/graph_outputs/{g_out.id}"
        if g_out.meta.type == "DIRECTORY":
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
