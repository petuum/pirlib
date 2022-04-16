import argparse
import dataclasses
import yaml

from .utils import package_pipelines, pipeline_def


def config_package_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p",
        "--pipeline",
        type=pipeline_def,
        action="append",
        required=True,
        help="pipeline to be packaged (package.module:name)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        help="path to output file (or - for stdout)",
    )
    parser.add_argument("--flatten", action="store_true", help="flatten pipeline(s)")
    parser.set_defaults(parser=parser, handler=_package_handler)


def _package_handler(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    package = package_pipelines(parser, args.pipeline, args.flatten)
    if args.output is not None:
        yaml.dump(dataclasses.asdict(package), args.output, sort_keys=False)
