from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict
from pirlib.pir import Node


@dataclass
class HandlerV1Context(object):
    node: Node
    states: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any):
        self.states[key] = value

    def get(self, key: str, default: Any =None) -> Any:
        return self.states.get(key, default)

    def reset(self, key: str) -> None:
        del self.states[key]

    def sync_states(self, context) -> None:
        self.states.update(context.states)


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

    def setup(
        self,
        context: HandlerV1Context,
    ) -> None:
        pass

    def teardown(
        self,
        context: HandlerV1Context,
    ) -> None:
        pass