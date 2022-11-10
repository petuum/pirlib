import argparse
import base64
import pickle
import sys
from typing import Any, Optional

import yaml

import pirlib.pir
from pirlib.backends import Backend
from pirlib.handlers.v1 import HandlerV1Context, HandlerV1Event


def encode(x):
    return base64.b64encode(pickle.dumps(x)).decode()


def decode(x):
    return pickle.loads(base64.b64decode(x.encode()))


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
        for node in graph.nodes:
            print(node)
