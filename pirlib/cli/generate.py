import argparse
import dacite
import importlib
import pathlib
import yaml

from pirlib.pir import Package


def config_generate_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("package", type=pathlib.Path)
    parser.add_argument("--target", type=str, required=True)
    parser.add_argument("-o", "--output", type=pathlib.Path)
    parser.set_defaults(parser=parser, handler=_generate_handler)


def _generate_handler(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.target.count(":") != 1:
        raise argparse.ArgumentTypeError(f"malformatted reference to backend class '{args.target}'")
    module_name, backend_name = args.target.split(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as err:
        raise argparse.ArgumentTypeError(f"{err}")
    try:
        backend_class = getattr(module, backend_name)
    except AttributeError as err:
        raise argparse.ArgumentTypeError(f"{err}")
    with open(args.package) as f:
        package = dacite.from_dict(data_class=Package, data=yaml.safe_load(f))
    backend = backend_class()
    backend.generate(package, args=args)
