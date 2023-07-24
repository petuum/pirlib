import argparse
import base64
import dataclasses
import logging
import os
import pathlib
import subprocess
import sys
import uuid

import yaml

from .utils import package_pipelines, pipeline_def


def config_dockerize_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", type=pathlib.Path, help="path to docker build context")
    parser.add_argument(
        "-p",
        "--pipeline",
        type=pipeline_def,
        action="append",
        required=True,
        help="pipeline to be packaged (package.module:name)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--auto",
        action="store_true",
        help="try to automatically generate the Dockerfile",
    )
    group.add_argument(
        "-f",
        "--file",
        type=pathlib.Path,
        help="path to the Dockerfile (only if not --auto)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        help="path to output file (or - for stdout)",
    )
    parser.add_argument("--flatten", action="store_true", help="flatten pipeline(s)")

    parser.add_argument("--docker_base_image", help="base docker image to be used.")
    
    parser.set_defaults(parser=parser, handler=_dockerize_handler)


def _dockerize_handler(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    package = package_pipelines(parser, args.pipeline, flatten=args.flatten)
    image = f"pircli-build:{uuid.uuid4()}"
    command = ["docker", "build", args.path, "-t", image]
    if args.auto:
        conda_env = yaml.dump(_infer_conda_env())
        print("=========== BEGIN INFERRED CONDA ENV ===========")
        print(conda_env.strip())
        print("===========  END INFERRED CONDA ENV  ===========")
        dockerfile = _generate_dockerfile(args.path, args.docker_base_image)
        print("========== BEGIN GENERATED DOCKERFILE ==========")
        print(dockerfile.strip())
        print("==========  END GENERATED DOCKERFILE  ==========")
        b64 = base64.b64encode(conda_env.encode()).decode()
        command.extend(["-f", "-", "--build-arg", f"CONDA_ENV_B64={b64}"])
    else:
        dockerfile = None
        if args.file is not None:
            command.extend(["-f", args.file])
    try:
        subprocess.run(command, input=dockerfile, text=True, check=True)
    except FileNotFoundError:
        sys.exit("ERROR: docker is required but was not found")
    except subprocess.CalledProcessError:
        sys.exit("ERROR: failed to build docker image")

    if "DOCKER_USER" in os.environ and "PIRLIB_REPO" in os.environ:
        pushed_image = f"{os.environ['DOCKER_USER']}/{os.environ['PIRLIB_REPO']}"
        tag_command = ["docker", "tag", image, pushed_image]
        push_command = [
            "docker",
            "push",
            pushed_image,
        ]
        try:
            subprocess.run(tag_command)
            subprocess.run(push_command)
        except FileNotFoundError:
            sys.exit("ERROR: docker is required but was not found")
        except subprocess.CalledProcessError:
            sys.exit("ERROR: failed to push the generated image")
        finally:
            image = pushed_image
    else:
        logging.warn("Docker username and PIRlib repo are undefined")

    for graph in package.graphs:
        for node in graph.nodes:
            entrypoint = node.entrypoints["main"]
            if entrypoint.image is None:
                entrypoint.image = image
    if args.output is not None:
        yaml.dump(dataclasses.asdict(package), args.output, sort_keys=False)


def _generate_dockerfile(context_path: pathlib.Path, docker_base_image: str) -> str:
    workdir = "/pircli/workdir"
    miniconda3 = "/opt/conda"
    pythonpath = _infer_pythonpath(context_path, workdir)
    base_image = docker_base_image

    print("=========== BASE DOCKER IMAGE ===========")
    print(base_image)

    # return "\n".join(
    #     [
    #         "FROM continuumio/miniconda3:4.12.0",
    #         "ARG CONDA_ENV_B64",
    #         "RUN echo $CONDA_ENV_B64 | base64 -d > /tmp/environment.yml",
    #         "RUN conda env create -n pircli -f /tmp/environment.yml",
    #         f"COPY . {workdir}",
    #         f"WORKDIR {workdir}",
    #         f"ENV PYTHONPATH={pythonpath}",
    #         f'ENV PATH="{miniconda3}/envs/pircli/bin":$PATH',
    #     ]
    # )

    return "\n".join([
        "FROM continuumio/miniconda3:latest AS base",
        "ARG CONDA_ENV_B64",
        "RUN echo $CONDA_ENV_B64 | base64 -d > /tmp/environment.yml",
        "RUN conda env create -n pircli -f /tmp/environment.yml",
        f"COPY . {workdir}",
        f"WORKDIR {workdir}",
        f"ENV PYTHONPATH={pythonpath}",
        f'ENV PATH="{miniconda3}/envs/pircli/bin":$PATH',
        "",
        f"FROM {base_image} AS final",
        "COPY --from=base /opt/conda/ /opt/conda/",
        "COPY --from=base /tmp/environment.yml /tmp/environment.yml",
        f"COPY --from=base {workdir} {workdir}",
        # "RUN conda env update -n pircli -f /tmp/environment.yml --prune",
        f"WORKDIR {workdir}",
        f"ENV PYTHONPATH={pythonpath}",
        f'ENV PATH="{miniconda3}/envs/pircli/bin":$PATH',
        'ENV PYSPARK_PYTHON=python3.8',
        'ENV PYSPARK_DRIVER_PYTHON=python3.8'
    ])


def _infer_pythonpath(context_path, workdir) -> str:
    paths = []
    hostpath = context_path.resolve()
    pythonpath = os.getenv("PYTHONPATH", "").split(os.pathsep)
    for idx, path in enumerate(pythonpath):
        if not path:
            continue
        abspath = pathlib.Path(path).resolve()
        if (
            len(hostpath.parts) <= len(abspath.parts)
            and hostpath.parts == abspath.parts[: len(hostpath.parts)]
        ):
            relparts = abspath.parts[len(hostpath.parts) :]
            paths.append(pathlib.Path(workdir).joinpath(*relparts).as_posix())
        else:
            sys.exit(
                f"ERROR: path '{path}' in PYTHONPATH is outside"
                f" of the docker build context '{context_path}'"
            )
    return os.pathsep.join(paths)


def _infer_conda_env() -> dict:
    # https://github.com/conda/conda/issues/9628
    try:
        command = ["conda", "env", "export", "--no-builds"]
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
        full = yaml.safe_load(result.stdout.strip())
        command.append("--from-history")
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
        hist = yaml.safe_load(result.stdout.strip())
    except FileNotFoundError:
        sys.exit("ERROR: conda is required for automatic dockerization")
    except subprocess.CalledProcessError:
        sys.exit("ERROR: could not infer current conda environment for automatic dockerization")
    env = {"channels": full["channels"], "dependencies": hist["dependencies"]}
    for idx, dep in enumerate(env["dependencies"]):
        if not isinstance(dep, str):
            continue
        prefix = dep[: dep.find("=") + 1] if "=" in dep else dep
        for dep2 in full["dependencies"]:
            if not isinstance(dep2, str):
                continue
            if dep2.startswith(prefix):
                env["dependencies"][idx] = dep2
                break
    for dep in full["dependencies"]:
        if isinstance(dep, dict) and "pip" in dep:
            env["dependencies"].append(dep)
    return env
