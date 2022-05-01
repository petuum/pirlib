from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

import pirlib.pir


class HandlerV1(object):
    @abstractmethod
    def get_input_type(self, input_name: str) -> type:
        raise NotImplementedError

    @abstractmethod
    def get_output_type(self, output_name: str) -> type:
        raise NotImplementedError

    @abstractmethod
    def run_handler(
        self,
        node: pirlib.pir.Node,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> None:
        raise NotImplementedError
