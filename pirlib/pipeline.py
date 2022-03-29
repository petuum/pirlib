import copy
import functools
import inspect
import typing

from typing import Any, Callable, Optional

from pirlib.backends.inproc import InprocBackend
from pirlib.graph import Package
from pirlib.trace import package_pipeline, pipeline_call


class PipelineInstance(object):

    def __init__(self, func, name, config=None):
        self._func = func
        self._name = name
        self._config = copy.deepcopy(config) if config else {}

    @property
    def func(self):
        return self._func

    @property
    def name(self):
        return self._name

    @property
    def config(self):
        return self._config

    @pipeline_call
    def __call__(self, *args, **kwargs):
        package = package_pipeline(self.func, self.name, self.config)
        inputs = {}
        sig = inspect.signature(self.func)
        for idx, (name, param) in enumerate(sig.parameters.items()):
            inputs[name] = args[idx] if idx < len(args) else kwargs[name]
        backend = InprocBackend()
        outputs = backend.execute(package, self.name, self.config,
                                  inputs=inputs)
        ret = [outputs[f"{idx}"] for idx in range(len(outputs))]
        return_type = typing.get_origin(sig.return_annotation)
        if return_type == tuple:
            return tuple(ret)
        return ret[0]


class PipelineDefinition(object):

    def __init__(
            self,
            func: Optional[Callable] = None,
            *,  # Keyword-only arguments below.
            name: Optional[str] = None,
            config: Optional[dict] = None,
        ):
        self._func = func
        self._name = name if name else getattr(func, "__name__", None)
        self._config = copy.deepcopy(config) if config else None

    @property
    def func(self):
        return self._func

    @property
    def name(self):
        return self._name

    @property
    def config(self):
        return self._config

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            wrapper = PipelineDefinition(
                func=args[0],
                name=self.name,
                config=self.config,
            )
            functools.update_wrapper(wrapper, args[0])
            return wrapper
        return self.instance(self.name)(*args, **kwargs)

    def instance(self, name: str) -> PipelineInstance:
        return PipelineInstance(self.func, name, config=self.config)

    def package(self) -> Package:
        return package_pipeline(self.func, self.name, self.config)


def pipeline(
        func: Optional[Callable] = None,
        *,  # Keyword-only arguments below.
        name: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> PipelineDefinition:
    wrapper = PipelineDefinition(
        func=func,
        name=name,
        config=config,
    )
    functools.update_wrapper(wrapper, func)
    return wrapper
