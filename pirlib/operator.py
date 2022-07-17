import contextvars
import copy
import functools
import inspect
import typeguard
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import pirlib.pir
from pirlib.backends.inproc import InprocBackend
from pirlib.handlers.v1 import HandlerV1
from pirlib.package import recurse_hint, operator_call, package_operator

_OP_CONTEXT = contextvars.ContextVar("_OP_CONTEXT")


@dataclass
class OperatorContext:
    config: Dict[str, Any]
    output: Any


def operator_context() -> OperatorContext:
    return _OP_CONTEXT.get()


class OperatorInstance(object):
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
        return self._config["framework"]

    @operator_call
    def __call__(self, *args, **kwargs):
        package = package_operator(self.defn)
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
        return recurse_hint(
            lambda name, hint: outputs[name], "return", sig.return_annotation
        )


class OperatorDefinition(HandlerV1):
    def __init__(
        self,
        func: Optional[Callable] = None,
        *,  # Keyword-only arguments below.
        config: Optional[dict] = None,
        name: Optional[str] = None,
    ):
        self._func = func if func is None else typeguard.typechecked(func)
        self._name = name if name else getattr(func, "__name__", None)
        self._config = config

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
        return self._config["framework"]

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            wrapper = OperatorDefinition(
                func=args[0],
                name=self.name,
                config=self.config,
            )
            functools.update_wrapper(wrapper, args[0])
            return wrapper
        return self.instance(self.name)(*args, **kwargs)

    def instance(self, name: str) -> OperatorInstance:
        return OperatorInstance(self, name, config=self.config)

    def get_input_type(self, input_name: str) -> type:
        sig = inspect.signature(self.func)
        for name, param in sig.parameters.items():
            if name == input_name:
                return param.annotation

    def get_output_type(self, output_name: str) -> type:
        pass

    def run_handler(
        self,
        node: pirlib.pir.Node,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> None:
        context = OperatorContext(node.configs, None)
        sig = inspect.signature(self.func)
        context.output = recurse_hint(
            lambda name, hint: outputs[name], "return", sig.return_annotation
        )
        args, kwargs = [], {}
        for param in sig.parameters.values():
            value = recurse_hint(
                lambda name, hint: inputs[name], param.name, param.annotation
            )
            if param.kind == param.KEYWORD_ONLY:
                kwargs[param.name] = value
            else:
                args.append(value)
        token = _OP_CONTEXT.set(context)
        try:
            return_value = self.func(*args, **kwargs)
        finally:
            _OP_CONTEXT.reset(token)
        recurse_hint(
            lambda n, h, v: outputs.__setitem__(n, v),
            "return",
            sig.return_annotation,
            return_value,
        )


def operator(
    func: Optional[Callable] = None,
    *,  # Keyword-only arguments below.
    name: Optional[str] = None,
    config: Optional[dict] = {},
    framework: Optional[pirlib.pir.Framework] = None,
) -> OperatorDefinition:
    config["framework" ] = None
    if framework:
        config["framework"] = {
            "name": framework.name,
            "version": framework.version,
        }
        
    wrapper = OperatorDefinition(
        func=func,
        name=name,
        config=config,
    )
    functools.update_wrapper(wrapper, func)
    return wrapper


operator.context = operator_context
