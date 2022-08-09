import copy
import functools
import inspect
import typeguard

from typing import Callable, Optional

from pirlib.backends.inproc import InprocBackend
from pirlib.package import package_pipeline, pipeline_call, recurse_hint
from pirlib.pir import Package


class PipelineInstance(object):
    def __init__(self, defn, name, config=None):
        self._defn = defn
        self._name = name
        self._config = copy.deepcopy(config) if config else {}

    @property
    def defn(self):
        return self._defn

    @property
    def func(self):
        return self.defn.func

    @property
    def name(self):
        return self._name

    @property
    def config(self):
        return self._config

    @pipeline_call
    def __call__(self, *args, **kwargs):
        package = package_pipeline(self.defn)
        inputs = {}
        sig = inspect.signature(self.func)
        for idx, param in enumerate(sig.parameters.values()):
            input_value = args[idx] if idx < len(args) else kwargs[param.name]
            recurse_hint(
                lambda name, hint, val: inputs.update({name: val}),
                param.name,
                param.annotation,
                input_value,
            )
        backend = InprocBackend()
        outputs = backend.execute(package, self.name, self.config, inputs=inputs)
        return recurse_hint(lambda name, hint: outputs[name], "return", sig.return_annotation)


class PipelineDefinition(object):
    def __init__(
        self,
        func: Optional[Callable] = None,
        *,  # Keyword-only arguments below.
        name: Optional[str] = None,
        config: Optional[dict] = None,
    ):
        self._func = func if func is None else typeguard.typechecked(func)
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
        return self.instance(self.name)(*args, **kwargs)

    def instance(self, name: str) -> PipelineInstance:
        return PipelineInstance(self, name, config=self.config)

    def package(self) -> Package:
        return package_pipeline(self)


def pipeline(
    func: Optional[Callable] = None,
    *,  # Keyword-only arguments below.
    name: Optional[str] = None,
    config: Optional[dict] = None,
) -> PipelineDefinition:
    def wrapper(func) -> PipelineDefinition:
        pipeline_dfn = PipelineDefinition(
            func=func,
            name=name,
            config=config,
        )
        functools.update_wrapper(pipeline_dfn, func)
        return pipeline_dfn

    if func:
        return wrapper(func)
    else:
        return wrapper
