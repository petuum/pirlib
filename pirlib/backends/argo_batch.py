import argparse
import base64
import pickle
import sys
from tkinter import W
from typing import Any, Dict, Optional

import yaml

import pirlib.pir
from pirlib.backends import Backend
from pirlib.handlers.v1 import HandlerV1Context, HandlerV1Event


def encode(x):
    return base64.b64encode(pickle.dumps(x)).decode()


def decode(x):
    return pickle.loads(base64.b64decode(x.encode()))


def create_template_from_node(
    graph_inputs_encoded: str, node: pirlib.pir.Node
) -> Dict[str, Any]:
    # print(node)
    name = node.id
    script = {}
    image = node.entrypoints["main"].image
    command = [
        "python",
        "-m",
        __name__,
        "node",
        encode(node),
        encode(graph_inputs_encoded),
    ]

    volume = {"name": "node_outputs", "mountPath": "/mnt/node_outputs"}

    template = {
        "name": name,
        "container": {"image": image, "command": command, "volumeMounts": [volume]},
    }
    print(yaml.dump(template, default_flow_style=False, sort_keys=False))
    return template


class ArgoBatchBackend(Backend):
    def execute_parser(self) -> Optional[argparse.ArgumentParser]:
        pass

    def execute(self) -> Optional[argparse.ArgumentParser]:
        pass

    def generate_parser(self) -> Optional[argparse.ArgumentParser]:
        pass

    def generate(
        self,
        package: pirlib.pir.Package,
        config: Optional[dict] = None,
        args: Optional[argparse.Namespace] = None,
    ) -> Any:

        output_name = args.output.parts[-1].strip(".yml")

        workflow = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {"generateName": f"{output_name}"},
            "spec": {},
        }

        # Currently only 1 graph is supported
        assert len(package.graphs)
        graph = package.graphs[0]  # FIXME: need to handle multiple graphs
        print(args)
        templates = []
        graph_inputs_encoded = encode(graph.inputs)
        graph_outputs_encoded = encode(graph.outputs)
        for i, node in enumerate(graph.nodes):
            # Using the first node as the entrypoint of the workflow.
            if i == 0:
                entrypoint = node.id

            # Creating a template for the current node.
            template = {}
            create_template_from_node(graph_inputs_encoded, node)
