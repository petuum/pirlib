import contextvars
import copy
import functools
import inspect
import typeguard
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import pirlib.pir
from pirlib.backends.inproc import InprocBackend
from pirlib.handlers.v1 import HandlerV1, HandlerV1Context, HandlerV1Event
from pirlib.package import recurse_hint, task_call, package_task
from pirlib.cache import cache_directory, fetch_directory


_TASK_CONTEXT = contextvars.ContextVar("_TASK_CONTEXT")


@dataclass
class TaskContext:
    config: Dict[str, Any]
    output: Any


def task_context() -> TaskContext:
    return _TASK_CONTEXT.get()


class TaskInstance(object):
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

    @property
    def framework(self):
        return self.defn.framework

    @task_call
    def __call__(self, *args, **kwargs):
        package = package_task(self.defn)
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


class TaskDefinition(HandlerV1):
    def __init__(
        self,
        func: Optional[Callable] = None,
        *,  # Keyword-only arguments below.
        name: Optional[str] = None,
        config: Optional[dict] = None,
        framework: Optional[pirlib.pir.Framework] = None,
        enable_cache: bool = False,
        cache_key_fn: Callable = None
    ):
        self._func = func if func is None else typeguard.typechecked(func)
        self._name = name if name else getattr(func, "__name__", None)
        self._config = copy.deepcopy(config) if config else None
        self._framework = framework
        self.enable_cache = enable_cache
        self.cache_key_fn = cache_key_fn

    @property
    def func(self):
        return self._func

    @property
    def name(self):
        return self._name

    @property
    def config(self):
        return self._config

    @property
    def framework(self):
        return self._framework

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            wrapper = TaskDefinition(
                func=args[0],
                name=self.name,
                config=self.config,
                framework=self.framework,
            )
            functools.update_wrapper(wrapper, args[0])
            return wrapper
        return self.instance(self.name)(*args, **kwargs)

    def instance(self, name: str) -> TaskInstance:
        return TaskInstance(self, name, config=self.config)

    def get_input_type(self, input_name: str) -> type:
        sig = inspect.signature(self.func)
        for name, param in sig.parameters.items():
            if name == input_name:
                return param.annotation

    def get_output_type(self, output_name: str) -> type:
        pass

    def run_handler(
        self,
        event: HandlerV1Event,
        context: HandlerV1Context,
    ) -> None:
        inputs, outputs = event.inputs, event.outputs
        sig = inspect.signature(self.func)
        task_context = TaskContext(context.node.config, None)
        task_context.output = recurse_hint(
            lambda name, hint: outputs[name], "return", sig.return_annotation
        )
        args, kwargs = [], {}
        for param in sig.parameters.values():
            value = recurse_hint(lambda name, hint: inputs[name], param.name, param.annotation)
            if param.kind == param.KEYWORD_ONLY:
                kwargs[param.name] = value
            else:
                args.append(value)
        token = _TASK_CONTEXT.set(task_context)
        try:
            if self.enable_cache:
                cache_key = self.cache_key_fn()
                ok = fetch_directory(dir_path=task_context.output, cache_key=cache_key)
                if not ok:
                    return_value = self.func(*args, **kwargs)
                    cache_status = cache_directory(task_context.output, cache_key)
                    if not cache_status:
                        raise ValueError("Key already exists, caching not possible")
                else:
                    return_value = task_context.output
            else:
                return_value = self.func(*args, **kwargs)
        finally:
            _TASK_CONTEXT.reset(token)
        recurse_hint(
            lambda n, h, v: outputs.__setitem__(n, v),
            "return",
            sig.return_annotation,
            return_value,
        )


def task(
    func: Optional[Callable] = None,
    *,  # Keyword-only arguments below.
    name: Optional[str] = None,
    config: Optional[dict] = None,
    framework: Optional[pirlib.pir.Framework] = None,
    enable_cache: bool = False,
    cache_key_fn: Callable = None
) -> TaskDefinition:
    if framework:
        if config is None:
            config = {}
        f_name = framework.name
        for k, v in framework.config.items():
            config[f"{f_name}/{k}"] = v
    
    if enable_cache and cache_key_fn == None:
        raise ValueError("Cache is enabled but cache_key_fn is not defined")

    wrapper = TaskDefinition(
        func=func,
        name=name,
        config=config,
        framework=framework,
        enable_cache = enable_cache,
        cache_key_fn = cache_key_fn
    )
    functools.update_wrapper(wrapper, func)
    return wrapper


task.context = task_context
