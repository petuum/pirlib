import argparse
from typing import Any, Optional

import pirlib.pir


class Backend(object):
    def generate_parser(self) -> Optional[argparse.ArgumentParser]:
        return None

    def execute_parser(self) -> Optional[argparse.ArgumentParser]:
        return None

    def generate(
        self,
        graph: pirlib.pir.Package,
        config: Optional[dict] = None,
        args: Optional[argparse.Namespace] = None,
    ) -> Any:
        raise NotImplementedError

    def execute(
        self,
        graph: pirlib.pir.Package,
        config: Optional[dict] = None,
        args: Optional[argparse.Namespace] = None,
    ) -> Any:
        raise NotImplementedError
