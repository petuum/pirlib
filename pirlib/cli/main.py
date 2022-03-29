import argparse
import sys

from .dockerize import config_dockerize_parser
from .execute import config_execute_parser
from .generate import config_generate_parser
from .package import config_package_parser


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    config_package_parser(
        subparsers.add_parser(
            "package",
            help="export pipelines for execution in current environment",
        )
    )

    config_execute_parser(
        subparsers.add_parser(
            "execute",
        )
    )

    config_generate_parser(
        subparsers.add_parser(
            "generate",
        )
    )

    config_dockerize_parser(
        subparsers.add_parser(
            "dockerize",
            help="export pipelines for execution in current environment",
        )
    )
    
    args = parser.parse_args()
    try:
        args.handler(args.parser, args)
    except KeyboardInterrupt:
        sys.exit(130)
