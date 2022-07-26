from abc import abstractmethod
from typing import Any, Dict


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
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        raise NotImplementedError
