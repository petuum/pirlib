import argparse
import base64
import os
import pickle
import re
import sys
from typing import Any, Dict, Optional, Tuple

import yaml

import pirlib.pir
from pirlib.backends import Backend
from pirlib.cache import CACHE_DIR
from pirlib.handlers.v1 import HandlerV1Context, HandlerV1Event


def encode(x):
    return base64.b64encode(pickle.dumps(x)).decode()


def decode(x):
    return pickle.loads(base64.b64decode(x.encode()))


argo_name = lambda x: re.sub("[^a-zA-Z0-9]", "-", x.strip())


def create_nfs_volume_spec(
    volume_name: str, is_file: bool, vol_type: str, readonly: bool = False, is_graph: bool = False
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Creates Kubernetes specs for defining NFS volumes.

    :param volume_name: Name of the volume, required for mount reference.
    :type volume_name: str
    :param is_file: True if the location is a file and False, if it's a directory.
    :type is_file: bool
    :param vol_type: `input` if the volume contains input data, `output` if the volume contains
    output data, `cache` if the volume contains cache data.
    :type is_type: str
    :param readonly: Defines if the volume should be read only, defaults to False.
    :type readonly: bool, optional
    :param is_graph: True if the volume will be attached at the graph level, defaults to False.
    :type is_gaph: bool, optional
    :raises RuntimeError: If the environment variables containing the NFS locations are
    not defined.
    :return: K8s specification for the NFS volume and mount information.
    :rtype: Tuple[Dict[str, Any], Dict[str, str]]
    """

    # Decide if volume will be attached at a node level or at a graph level
    if is_graph:
        attach_level = "graph"
    else:
        attach_level = "node"

    # Construct the name for the env var that contains the input directory/file path.
    if vol_type == "input":
        path_env_var = f"INPUT_{volume_name}"
        mount_path = f"/mnt/graph_inputs/{volume_name}"
    elif vol_type == "output":
        path_env_var = "OUTPUT"
        mount_path = f"/mnt/{attach_level}_outputs"
    elif vol_type == "cache":
        path_env_var = "CACHE"
        mount_path = str(CACHE_DIR)

    for var in ("NFS_SERVER", path_env_var):
        if var not in os.environ:
            raise RuntimeError(f"Required environment variable `{var}` is undefined.")

    spec = {"name": argo_name(volume_name)}
    path = os.environ[path_env_var]

    # If the data is coming from a file. The path will include only till the parent directory
    # of the file.
    if is_file:
        split_path = path.split("/")
        path = "/".join(split_path[:-1])
        filename = split_path[-1]

    nfs = {
        "server": os.environ["NFS_SERVER"],
        "path": path,
        "readOnly": readonly,
    }
    spec["nfs"] = nfs

    # Create mounting spec for the volume.
    mount_spec = {
        "name": argo_name(volume_name),
        "mountPath": mount_path,
    }

    # If the input source is a file, add the filename as a subpath.
    if is_file:
        mount_spec["subPath"] = filename

    return spec, mount_spec


def create_template_from_node(
    graph_inputs_encoded: str,
    node: pirlib.pir.Node,
) -> Dict[str, Any]:
    """Generates an Argo template dictionary from the provided Node.

    :param graph_inputs_encoded: base64 encoding of the graph inputs.
    :type graph_inputs_encoded: str
    :param node: `Node` of a graph.
    :type node: pirlib.pir.Node
    :return: A dictionary containing the fields required to generate
    an Argo template for the given node.
    :rtype: Dict[str, Any]
    """
    name = node.id
    image = node.entrypoints["main"].image
    command = [
        "python",
        "-m",
        __name__,
        "node",
        encode(node),
        graph_inputs_encoded,
    ]

    # Obtain specs for the output volume.
    op_volume, op_volume_mount = create_nfs_volume_spec(
        volume_name="node_outputs", is_file=False, vol_type="output"
    )

    # Define input volumes to be mounted.
    volumes = [op_volume]
    volume_mounts = [op_volume_mount]
    dependencies = []

    # If the node has a valid graph input source,
    # mount the respective host system's file to the input volume
    for inp in node.inputs:
        is_file = inp.iotype == "FILE"
        if inp.source.graph_input_id:
            inp_id = inp.source.graph_input_id

            # Create NFS volume spec.
            inp_volume_spec, mount_spec = create_nfs_volume_spec(
                inp_id, is_file, vol_type="input", readonly=True
            )

            # Add the volume to the volume list.
            volumes.append(inp_volume_spec)

            # Add the volume mount spec to the volume mount list.
            volume_mounts.append(mount_spec)

        # Add temporary field for defining dependencies.
        if inp.source.node_id:
            dependencies.append(argo_name(inp.source.node_id))

    # Mount cache volume if Cache is enabled.
    if node.config.get("cache"):
        cache_volume_spec, cache_mount_spec = create_nfs_volume_spec(
            "cache_dir", is_file=False, vol_type="cache", readonly=False, is_graph=False
        )

        # Add the volume to the volume list.
        volumes.append(cache_volume_spec)

        # Add the volume mount spec to the volume mount list.
        volume_mounts.append(cache_mount_spec)

    # Create the template dictionary.
    template = {
        "name": argo_name(name),
        "container": {
            "image": image,
            "command": command,
            "volumeMounts": volume_mounts,
        },
        "volumes": volumes,
        "dependencies": dependencies,
    }

    return template


def create_template_from_graph(
    graph_outputs_encoded: str, graph: pirlib.pir.Graph
) -> Dict[str, Any]:
    """Generates an Argo template dictionary from the provided Graph.

    :param graph_outputs_encoded: base64 encoding of the graph outputs.
    :type graph_outputs_encoded: str
    :param graph: A PIRlib Graph object.
    :type graph: pirlib.pir.Graph
    :return: An Argo template dict for the Graph object.
    :rtype: Dict[str, Any]
    """
    name = graph.id
    image = graph.nodes[0].entrypoints["main"].image
    command = ["python", "-m", __name__, "graph", graph_outputs_encoded]

    # Obtain specs for the output volume.
    op_volume, op_volume_mount = create_nfs_volume_spec(
        volume_name="node_outputs", is_file=False, vol_type="output"
    )

    # Define input volumes to be mounted.
    volumes = [op_volume]
    volume_mounts = [op_volume_mount]

    for inp in graph.inputs:
        inp_id = inp.id
        is_file = inp.iotype == "FILE"

        # Create NFS volume spec.
        inp_volume_spec, inp_mount_spec = create_nfs_volume_spec(
            inp_id, is_file, vol_type="input", readonly=True, is_graph=True
        )

        # Add the volume spec to the volume list.
        volumes.append(inp_volume_spec)

        # Add the mount spec to the mount list.
        volume_mounts.append(inp_mount_spec)

    if graph.outputs:
        graph_op_volume_spec, graph_op_mount_spec = create_nfs_volume_spec(
            "graph_outputs", is_file=False, vol_type="output", is_graph=True
        )
        volumes.append(graph_op_volume_spec)
        volume_mounts.append(graph_op_mount_spec)

    template = {
        "name": argo_name(name),
        "container": {
            "image": image,
            "command": command,
            "volumeMounts": volume_mounts,
        },
        "volumes": volumes,
    }

    return template


def argo_refactor(workflow_yaml: str) -> str:
    """Applies Argo specific refactoring on the
    generated YAML file string.

    :param workflow_yaml: The YAML string defining an Argo workflow.
    :type workflow_yaml: str
    :return: Argo compatiable YAML string.
    :rtype: str
    """
    workflow_yaml = workflow_yaml.replace("true", "yes")
    workflow_yaml = workflow_yaml.replace("false", "no")

    return workflow_yaml


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
    ) -> None:
        """Generates an YAML file that defines an Argo workflow replicating the input package Graph.

        :param package: PIRlib package containing a Graph.
        :type package: pirlib.pir.Package
        :param config: Parser config, defaults to None
        :type config: Optional[dict], optional
        :param args: Pipeline arguments, defaults to None
        :type args: Optional[argparse.Namespace], optional
        """

        output_name = args.output.parts[-1].strip(".yml")

        workflow = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {"generateName": f"{output_name}-"},
            "spec": {},
        }

        # Currently only 1 graph is supported
        assert len(package.graphs)
        graph = package.graphs[0]  # FIXME: need to handle multiple graphs
        templates = []
        graph_inputs_encoded = encode(graph.inputs)
        graph_outputs_encoded = encode(graph.outputs)

        # Generate template for the nodes.
        for node in graph.nodes:
            # Creating a template for the current node.
            template = create_template_from_node(graph_inputs_encoded, node)
            # NOTE: Need to replace true and false with yes and no in the final string.
            templates.append(template)

        # Generate template for the graph.
        graph_template = create_template_from_graph(graph_outputs_encoded, graph)

        # Add all the nodes as the dependency for the graph.
        graph_template["dependencies"] = [t["name"] for t in templates]

        templates.append(graph_template)

        # Modify Node template names to include graph ID.
        for template in templates:
            template["name"] = argo_name(f"{template['name']}")

        # Create the DAG entrypoint.
        dag = {"name": argo_name(f"DAG-{graph.id}"), "dag": {"tasks": []}}

        for template in templates:
            name = template["name"]
            task = {
                "name": name,
                "template": f"{name}-template",
                "dependencies": [argo_name(f"{tname}") for tname in template.pop("dependencies")],
            }
            dag["dag"]["tasks"].append(task)
            template["name"] += "-template"
        templates.append(dag)

        workflow["spec"]["entrypoint"] = dag["name"]
        workflow["spec"]["templates"] = templates

        # Generate YAML string.
        workflow_yaml = yaml.dump(workflow, sort_keys=False)

        # Refactor.
        workflow_yaml = argo_refactor(workflow_yaml)

        # Wrirting the workflow YAML to disk.
        if args and args.output:
            with open(args.output, "w") as f:
                f.write(workflow_yaml)


def run_node(node, graph_inputs):
    import importlib
    import pathlib

    import pandas

    from pirlib.iotypes import DirectoryPath, FilePath

    module_name, handler_name = node.entrypoints["main"].handler.split(":")
    handler = getattr(importlib.import_module(module_name), handler_name)
    inputs = {}
    for inp in node.inputs:
        if inp.source.node_id is not None:
            path = f"/mnt/node_outputs/{inp.source.node_id}/{inp.source.output_id}"
        if inp.source.graph_input_id is not None:
            path = f"/mnt/graph_inputs/{inp.source.graph_input_id}"
        if inp.iotype == "DIRECTORY":
            inputs[inp.id] = DirectoryPath(path)
        elif inp.iotype == "FILE":
            inputs[inp.id] = FilePath(path)
        elif inp.iotype == "DATAFRAME":
            inputs[inp.id] = pandas.read_csv(path)
        else:
            raise TypeError(f"unsupported iotype {inp.iotype}")
    outputs = {}
    for out in node.outputs:
        path = f"/mnt/node_outputs/{node.id}/{out.id}"
        if out.iotype == "DIRECTORY":
            outputs[out.id] = DirectoryPath(path)
            outputs[out.id].mkdir(parents=True, exist_ok=True)
        elif out.iotype == "FILE":
            outputs[out.id] = FilePath(path)
            outputs[out.id].parents[0].mkdir(parents=True, exist_ok=True)
        else:
            outputs[out.id] = None
    events = HandlerV1Event(inputs, outputs)
    context = HandlerV1Context(node)
    handler.run_handler(events, context)
    for out in node.outputs:
        path = f"/mnt/node_outputs/{node.id}/{out.id}"
        if out.iotype == "DATAFRAME":
            pathlib.Path(path).parents[0].mkdir(parents=True, exist_ok=True)
            outputs[out.id].to_csv(path)


def run_graph(graph_outputs):
    import shutil

    for g_out in graph_outputs:
        source = g_out.source
        if source.node_id is not None:
            path_from = f"/mnt/node_outputs/{source.node_id}/{source.output_id}"
        if source.graph_input_id is not None:
            path_from = f"/mnt/graph_inputs/{source.graph_input_id}"
        path_to = f"/mnt/graph_outputs/{g_out.id}"
        if g_out.iotype == "DIRECTORY":
            shutil.copytree(path_from, path_to, dirs_exist_ok=True)
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
    pass
