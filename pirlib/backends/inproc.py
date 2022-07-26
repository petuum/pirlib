import argparse
import importlib
import pandas
import tempfile
from typing import Any, Dict, Optional

import pirlib.pir
import pirlib.iotypes
from pirlib.backends import Backend
from pirlib.context import TaskContext
from pirlib.iotypes import DirectoryPath, FilePath
from pirlib.utils import find_by_id


class InprocBackend(Backend):
    def execute(
        self,
        package: pirlib.pir.Package,
        graph_name: str,
        config: Optional[dict] = None,
        args: Optional[argparse.Namespace] = None,
        *,  # Keyword-only arguments below.
        inputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        graph = package.flatten_graph(graph_name, validate=True)
        inputs = {} if inputs is None else inputs
        if args is not None:
            for spec in args.input:
                inp = find_by_id(graph.inputs, spec.name)
                if inp.iotype == "DIRECTORY":
                    inputs[spec.name] = DirectoryPath(spec.url.path)
                elif inp.iotype == "FILE":
                    inputs[spec.name] = FilePath(spec.url.path)
                elif inp.iotype == "DATAFRAME":
                    if spec.fmt == "csv":
                        inputs[spec.name] = pandas.read_csv(spec.url.path)
        # Validate all required inputs are provided.
        for inp in graph.inputs:
            if inp.id not in inputs:
                raise ValueError(f"missing input '{inp.id}'")
        # Execute nodes one at a time.
        node_outputs = {}
        while True:
            remaining_nodes = [node for node in graph.nodes if node.id not in node_outputs]
            if not remaining_nodes:
                break
            # Find a node that has all inputs ready.
            for node in remaining_nodes:
                node_inputs = {}
                for inp in node.inputs:
                    if inp.source.graph_input_id is not None:
                        # Node input provided by graph input
                        node_inputs[inp.id] = inputs[inp.source.graph_input_id]
                    if inp.source.node_id is not None:
                        # Node input provided by other node's (provider) output
                        if inp.source.node_id not in node_outputs:
                            # Provider hasn't been executed yet
                            break
                        if inp.source.output_id not in node_outputs[inp.source.node_id]:
                            # Provider's output is not ready
                            break
                        node_inputs[inp.id] = node_outputs[inp.source.node_id][inp.source.output_id]
                else:
                    break
            else:
                raise RuntimeError("could not finish execution")
            # Execute node and collect its outputs.
            node_outputs[node.id] = self._execute_node(node, node_inputs)
        outputs = {}
        for out in graph.outputs:
            if out.source.node_id is not None:
                outputs[out.id] = node_outputs[out.source.node_id][out.source.output_id]
            if out.source.graph_input_id is not None:
                outputs[out.id] = inputs[out.source.graph_input_id]
        if args is not None:
            for spec in args.output:
                out = find_by_id(graph.outputs, spec.name)
                if out.iotype == "DATAFRAME":
                    outputs[spec.name].to_csv(spec.url.path)
        return outputs

    def _execute_node(self, node: pirlib.pir.Node, inputs: Dict[str, Any]):
        module_name, handler_name = node.entrypoints["main"].handler.split(":")
        handler = getattr(importlib.import_module(module_name), handler_name)
        outputs = {}
        for out in node.outputs:
            if out.iotype == "DIRECTORY":
                outputs[out.id] = DirectoryPath(tempfile.mkdtemp())
            elif out.iotype == "FILE":
                outputs[out.id] = FilePath(tempfile.mkstemp()[1])
            else:
                outputs[out.id] = None
        event = {
            "inputs": inputs,
            "outputs": outputs,
        }
        context = TaskContext(node.config, None)
        handler.run_handler(event, context)
        return outputs
