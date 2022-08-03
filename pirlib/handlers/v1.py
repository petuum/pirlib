from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class HandlerContext(object):
    node_config: Dict[str, Any]


@dataclass
class HandlerEvent(object):
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]


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
        event: HandlerEvent,
        context: HandlerContext,
    ) -> None:
        raise NotImplementedError
