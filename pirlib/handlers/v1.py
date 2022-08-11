from abc import abstractmethod
from dataclasses import dataclass
from logging import Logger
from typing import Any, Dict, Optional


@dataclass
class HandlerV1Context(object):
    node: Dict[str, Any]
    logger: Optional[Logger] = None


@dataclass
class HandlerV1Event(object):
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
        event: HandlerV1Event,
        context: HandlerV1Context,
    ) -> None:
        raise NotImplementedError

    def setup_handler(
        self,
        context: HandlerV1Context,
    ) -> None:
        pass

    def teardown_handler(
        self,
        context: HandlerV1Context,
    ) -> None:
        pass
