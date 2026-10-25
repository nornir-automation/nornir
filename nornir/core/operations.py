"""Operations: actions defined once with a typed input and output, implemented per platform.

An Operation is a contract: a subclass of :class:`Operation` with a ``name``, an input
model and an output model. Implementations are plain tasks, registered for one
``(operation, platform, connection)`` key with :meth:`OperationRegistry.register` or
through the ``nornir.plugins.operation_tasks`` entry-point group. Run an Operation with
:meth:`nornir.core.Nornir.run_operation`; each host runs the task registered for its
platform and returns a result typed with the output model.
"""

from __future__ import annotations

import difflib
import importlib.metadata
import inspect
import logging
import re
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Literal, TypeVar, get_args, get_origin

from nornir.core.exceptions import (
    AsyncTaskOnSyncRunError,
    OperationAlreadyRegisteredError,
    OperationContractNotFoundError,
    OperationEntryPointError,
    OperationInputError,
    OperationNotRegisteredError,
    OperationOutputError,
    SyncTaskOnAsyncRunError,
)
from nornir.core.task import DEFAULT_SEVERITY_LEVEL, Result, Task, _get_task_name, _is_async_task

if TYPE_CHECKING:
    from nornir.core import Nornir
    from nornir.core.inventory import Host
    from nornir.core.processor import Processors

logger = logging.getLogger(__name__)

InT = TypeVar("InT")
OutT = TypeVar("OutT")

OPERATIONS_GROUP = "nornir.plugins.operations"
"""Entry-point group of Operation classes; the entry-point name is the Operation name."""

OPERATION_TASKS_GROUP = "nornir.plugins.operation_tasks"
"""Entry-point group of implementations, named ``<operation>.<platform>.<connection>``."""


class Operation(Generic[InT, OutT]):
    """A contract with a typed input and a typed output, and no vendor logic.

    Subclass it with the two model classes as type arguments and set ``name``::

        @dataclass
        class GetConfigInput:
            retrieve: str = "running"

        @dataclass
        class GetConfigOutput:
            config: str

        class GetConfig(Operation[GetConfigInput, GetConfigOutput]):
            name = "get_config"

    ``input_model`` and ``output_model`` are set from the type arguments, and the class is
    registered under ``name`` when it is defined. A subclass without its own ``name`` is a
    base for other Operations and is not registered.

    Raises:
        TypeError: a type argument is not a class
        nornir.core.exceptions.OperationAlreadyRegisteredError: another class already
            uses ``name``

    """

    name: ClassVar[str]
    input_model: ClassVar[type[Any]]
    output_model: ClassVar[type[Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for base in cls.__dict__.get("__orig_bases__", ()):
            origin = get_origin(base)
            if isinstance(origin, type) and issubclass(origin, Operation):
                models = get_args(base)
                if not all(isinstance(model, type) for model in models):
                    msg = (
                        f"{cls.__qualname__}: the type arguments of Operation must be classes, "
                        f"got {models!r}"
                    )
                    raise TypeError(msg)
                cls.input_model, cls.output_model = models
        if "name" not in cls.__dict__:
            return
        if not hasattr(cls, "input_model"):
            msg = (
                f"{cls.__qualname__}: give the input and output models as type arguments, "
                "for example Operation[MyInput, MyOutput]"
            )
            raise TypeError(msg)
        OperationRegistry._register_contract(cls)


@dataclass(frozen=True)
class RegistrationSource:
    """Where a registration came from.

    Arguments:
        kind: ``entry_point`` for a registration declared by an installed distribution,
            ``call`` for :meth:`OperationRegistry.register` or an Operation class definition
        module: Module of the task or of the Operation class
        qualname: Qualified name of the task or of the Operation class
        distribution: Name of the distribution, for an entry point
        entry_point: Name of the entry point, for an entry point

    """

    kind: Literal["entry_point", "call"]
    module: str
    qualname: str
    distribution: str | None = None
    entry_point: str | None = None

    def __str__(self) -> str:
        if self.kind == "entry_point":
            return f"distribution {self.distribution!r} (entry point {self.entry_point!r})"
        return f"{self.module}.{self.qualname}"


@dataclass(frozen=True)
class Registration:
    """One task registered for one ``(operation, platform, connection)`` key.

    Arguments:
        operation: Name of the Operation
        platform: Platform of the hosts the task runs for, as written in the inventory
        connection: Name of the connection the task uses
        task: The task
        kind: ``sync`` or ``async``: the runners the task can run on
        source: Where the registration came from

    """

    operation: str
    platform: str
    connection: str
    task: Callable[..., Any]
    kind: Literal["sync", "async"]
    source: RegistrationSource


@dataclass(frozen=True)
class OperationInfo:
    """One known Operation, as listed by :meth:`OperationRegistry.operations`.

    Arguments:
        name: Name of the Operation
        operation: The Operation class, or ``None`` when tasks are registered for the name
            but no class defines it
        input_model: The input model, or ``None`` without a class
        output_model: The output model, or ``None`` without a class
        implementations: The registered tasks, sorted by platform and connection

    """

    name: str
    operation: type[Operation[Any, Any]] | None
    input_model: type[Any] | None
    output_model: type[Any] | None
    implementations: tuple[Registration, ...]


def _source_of(obj: Any) -> RegistrationSource:
    return RegistrationSource(
        kind="call",
        module=getattr(obj, "__module__", None) or "<unknown>",
        qualname=getattr(obj, "__qualname__", None) or type(obj).__qualname__,
    )


class OperationRegistry:
    """The Operations and their implementations known to the process.

    Entry points of installed distributions are loaded the first time the registry is
    read, not when Nornir is initialized, so a broken package affects only programs that
    use Operations. Every method is safe to call from any thread.
    """

    _contracts: ClassVar[dict[str, type[Operation[Any, Any]]]] = {}
    _registrations: ClassVar[dict[tuple[str, str, str], Registration]] = {}
    _loaded: ClassVar[bool] = False
    # Reentrant: loading an entry point imports a module that defines an Operation class.
    _lock: ClassVar[threading.RLock] = threading.RLock()

    @classmethod
    def register(
        cls,
        *,
        operation: str,
        platform: str,
        connection: str,
        task: Callable[..., Any],
        replace: bool = False,
    ) -> Registration:
        """Register ``task`` as the implementation of ``operation`` for a platform.

        Registering the same task again for the same key does nothing. The Operation class
        does not have to be defined yet.

        Arguments:
            operation: Name of the Operation
            platform: Platform of the hosts, as written in the inventory
            connection: Name of the connection the task uses
            task: The task: ``def task(task: Task, params: In) -> Out | Result[Out]``, or
                its ``async def`` form
            replace: Replace a different task already registered for the key

        Returns:
            The registration.

        Raises:
            ValueError: ``operation``, ``platform`` or ``connection`` is empty or ``None``
            nornir.core.exceptions.OperationAlreadyRegisteredError: a different task is
                registered for the key and ``replace`` is false

        """
        return cls._register(operation, platform, connection, task, _source_of(task), replace)

    @classmethod
    def _register(
        cls,
        operation: str,
        platform: str,
        connection: str,
        task: Callable[..., Any],
        source: RegistrationSource,
        replace: bool,
    ) -> Registration:
        for field, value in (
            ("operation", operation),
            ("platform", platform),
            ("connection", connection),
        ):
            if not value or not isinstance(value, str):
                msg = f"{field} must be a non-empty string, got {value!r}"
                raise ValueError(msg)
        key = (operation, platform, connection)
        registration = Registration(
            operation=operation,
            platform=platform,
            connection=connection,
            task=task,
            kind="async" if _is_async_task(task) else "sync",
            source=source,
        )
        with cls._lock:
            existing = cls._registrations.get(key)
            if existing is not None and existing.task is not task and not replace:
                raise OperationAlreadyRegisteredError(
                    operation, ".".join(key), str(existing.source), str(source)
                )
            if existing is not None and existing.task is task:
                return existing
            cls._registrations[key] = registration
        return registration

    @classmethod
    def deregister(cls, *, operation: str, platform: str, connection: str) -> None:
        """Remove the task registered for the key, if any."""
        with cls._lock:
            cls._registrations.pop((operation, platform, connection), None)

    @classmethod
    def get(cls, operation: str, platform: str, connection: str) -> Registration:
        """Return the registration for the key.

        Returns:
            The registration.

        Raises:
            nornir.core.exceptions.OperationNotRegisteredError: no task is registered for
                the key

        """
        cls.load()
        with cls._lock:
            registration = cls._registrations.get((operation, platform, connection))
            if registration is None:
                raise OperationNotRegisteredError(
                    operation, platform, connection, cls._keys_of(operation)
                )
            return registration

    @classmethod
    def contract(cls, name: str) -> type[Operation[Any, Any]]:
        """Return the Operation class defined under ``name``.

        Returns:
            The Operation class.

        Raises:
            nornir.core.exceptions.OperationContractNotFoundError: no class defines
                ``name``

        """
        cls.load()
        with cls._lock:
            operation = cls._contracts.get(name)
            if operation is None:
                raise OperationContractNotFoundError(name, tuple(sorted(cls._contracts)))
            return operation

    @classmethod
    def operations(cls) -> list[OperationInfo]:
        """List every known Operation, with its models and its implementations.

        An Operation is known once its class is defined, or once a task is registered for
        its name. No task is called.

        Returns:
            One entry per Operation name, sorted by name.

        """
        cls.load()
        with cls._lock:
            names = set(cls._contracts) | {key[0] for key in cls._registrations}
            infos = []
            for name in sorted(names):
                operation = cls._contracts.get(name)
                implementations = tuple(
                    registration
                    for key, registration in sorted(cls._registrations.items())
                    if key[0] == name
                )
                infos.append(
                    OperationInfo(
                        name=name,
                        operation=operation,
                        input_model=operation.input_model if operation else None,
                        output_model=operation.output_model if operation else None,
                        implementations=implementations,
                    )
                )
            return infos

    @classmethod
    def load(cls) -> None:
        """Load the Operations and implementations declared by installed distributions.

        Reads the ``nornir.plugins.operations`` and ``nornir.plugins.operation_tasks``
        entry-point groups once per process. If it raises, the next call tries again.

        Raises:
            nornir.core.exceptions.OperationEntryPointError: an entry point is malformed
            nornir.core.exceptions.OperationAlreadyRegisteredError: two registrations
                conflict

        """
        with cls._lock:
            if cls._loaded:
                return
            for entry_point in importlib.metadata.entry_points(group=OPERATIONS_GROUP):
                cls._load_contract(entry_point)
            for entry_point in importlib.metadata.entry_points(group=OPERATION_TASKS_GROUP):
                cls._load_task(entry_point)
            cls._loaded = True

    @staticmethod
    def _distribution(entry_point: importlib.metadata.EntryPoint) -> str:
        return entry_point.dist.name if entry_point.dist is not None else "<unknown>"

    @classmethod
    def _load_contract(cls, entry_point: importlib.metadata.EntryPoint) -> None:
        operation = entry_point.load()
        if not (
            isinstance(operation, type)
            and issubclass(operation, Operation)
            and operation.__dict__.get("name") == entry_point.name
        ):
            raise OperationEntryPointError(
                entry_point.name,
                cls._distribution(entry_point),
                entry_point.name,
                f"in {OPERATIONS_GROUP!r}, the value must be an Operation class whose name "
                f"is {entry_point.name!r}.",
            )

    @classmethod
    def _load_task(cls, entry_point: importlib.metadata.EntryPoint) -> None:
        distribution = cls._distribution(entry_point)
        parts = entry_point.name.split(".")
        if len(parts) != 3 or not all(parts):  # noqa: PLR2004 - operation, platform, connection
            raise OperationEntryPointError(
                parts[0],
                distribution,
                entry_point.name,
                f"in {OPERATION_TASKS_GROUP!r}, the name must be "
                "'<operation>.<platform>.<connection>'.",
            )
        task = entry_point.load()
        source = RegistrationSource(
            kind="entry_point",
            module=getattr(task, "__module__", None) or entry_point.module,
            qualname=getattr(task, "__qualname__", None) or entry_point.attr,
            distribution=distribution,
            entry_point=entry_point.name,
        )
        operation, platform, connection = parts
        cls._register(operation, platform, connection, task, source, replace=False)

    @classmethod
    def _register_contract(cls, operation: type[Operation[Any, Any]]) -> None:
        name = operation.name
        with cls._lock:
            existing = cls._contracts.get(name)
            # The same definition executed again (a notebook cell, a reloaded module)
            # replaces the class it defined before.
            if existing is not None and (existing.__module__, existing.__qualname__) != (
                operation.__module__,
                operation.__qualname__,
            ):
                raise OperationAlreadyRegisteredError(
                    name, None, str(_source_of(existing)), str(_source_of(operation))
                )
            cls._contracts[name] = operation

    @classmethod
    def _keys_of(cls, operation: str) -> tuple[str, ...]:
        return tuple(
            sorted(f"{key[1]}.{key[2]}" for key in cls._registrations if key[0] == operation)
        )

    @classmethod
    def _reset(cls) -> None:
        """Forget every registration and mark the entry points as not loaded; for tests."""
        with cls._lock:
            cls._contracts.clear()
            cls._registrations.clear()
            cls._loaded = False


_UNEXPECTED_KEYWORD = re.compile(r"unexpected keyword argument '(?P<name>[^']+)'")


def _describe_input_error(model: type[Any], error: Exception) -> str:
    match = _UNEXPECTED_KEYWORD.search(str(error)) if isinstance(error, TypeError) else None
    if match is None:
        return f"{type(error).__name__}: {error}"
    field = match["name"]
    reason = f"unexpected field {field!r}"
    try:
        fields = list(inspect.signature(model).parameters)
    except (TypeError, ValueError):
        fields = []
    close = difflib.get_close_matches(field, fields, n=1)
    if close:
        reason += f" (did you mean {close[0]!r}?)"
    return reason


def _build_input(operation: str, model: type[Any], value: Any, host_name: str | None = None) -> Any:
    """Build the input of an Operation from what the caller passed.

    ``None`` builds the model with no argument, an instance of the model is used as it
    is, and anything else goes to the model's ``model_validate`` when it has one, or is
    passed as keyword arguments when it is a mapping.

    Returns:
        An instance of ``model``.

    Raises:
        nornir.core.exceptions.OperationInputError: the input cannot be built

    """
    if isinstance(value, model):
        return value
    validate = getattr(model, "model_validate", None)
    if value is not None and not callable(validate) and not isinstance(value, Mapping):
        raise OperationInputError(
            operation,
            f"expected {model.__name__}, a mapping of its fields, or a callable that "
            f"receives the host, got {type(value).__name__!r}",
            host_name,
        )
    try:
        if value is None:
            return model()
        if callable(validate):
            return validate(value)
        return model(**value)
    except Exception as e:
        raise OperationInputError(operation, _describe_input_error(model, e), host_name) from e


def _is_per_host(params: Any, model: type[Any]) -> bool:
    return (
        callable(params)
        and not isinstance(params, type | Mapping)
        and not isinstance(params, model)
    )


def _not_resolved(_task: Task, **_kwargs: Any) -> None:
    """Stand in for the task of an Operation until each host selects its own.

    Raises:
        RuntimeError: always; the runners never call it

    """
    msg = "the task of an Operation is selected when the host starts"
    raise RuntimeError(msg)


class _OperationTask(Task):
    """A task that selects its implementation when each host starts.

    The selected task is called from the same line of :class:`Task` as any other task,
    so tracebacks and debuggers show no extra frame.
    """

    def __init__(
        self,
        operation: type[Operation[Any, Any]],
        connection: str,
        params: Any,
        per_host: bool,
        nornir: Nornir,
        global_dry_run: bool,
        processors: Processors,
        name: str | None = None,
        severity_level: int = DEFAULT_SEVERITY_LEVEL,
    ) -> None:
        super().__init__(
            _not_resolved,
            nornir,
            global_dry_run,
            processors,
            name=name or operation.name,
            severity_level=severity_level,
        )
        self.operation = operation
        self.connection = connection
        self.params_source = params
        self.per_host = per_host

    def copy(self) -> _OperationTask:
        """Return a copy of this task with no host, no results and no selected task.

        Returns:
            A task for the same Operation, connection and input.

        """
        return _OperationTask(
            self.operation,
            self.connection,
            self.params_source,
            self.per_host,
            self.nornir,
            self.global_dry_run,
            self.processors,
            self.name,
            self.severity_level,
        )

    def _resolve_call(self, host: Host, asynchronous: bool) -> None:
        operation = self.operation.name
        if host.platform is None:
            raise OperationNotRegisteredError(operation, None, self.connection, host_name=host.name)
        try:
            registration = OperationRegistry.get(operation, host.platform, self.connection)
        except OperationNotRegisteredError as e:
            raise OperationNotRegisteredError(
                operation, host.platform, self.connection, e.registered, host.name
            ) from None
        task_name = _get_task_name(registration.task)
        if asynchronous and registration.kind == "sync":
            raise SyncTaskOnAsyncRunError(task_name, operation, host.name)
        if not asynchronous and registration.kind == "async":
            raise AsyncTaskOnSyncRunError(task_name, operation, host.name)
        value = self.params_source
        if self.per_host:
            try:
                value = self.params_source(host)
            except Exception as e:
                raise OperationInputError(
                    operation, f"the params callable raised {e!r}", host.name
                ) from e
            value = _build_input(operation, self.operation.input_model, value, host.name)
        self.task = registration.task
        self.params = {"params": value}

    def _check_result(self, result: Result) -> Result:
        output_model = self.operation.output_model
        if result.failed or isinstance(result.result, output_model):
            return result
        error = OperationOutputError(
            self.operation.name,
            _get_task_name(self.task),
            type(result.result).__name__,
            output_model.__name__,
            self.host.name,
        )
        logger.error("Host %r: %s", self.host.name, error)
        return Result(
            result.host,
            result=str(error),
            changed=result.changed,
            diff=result.diff,
            failed=True,
            exception=error,
        )
