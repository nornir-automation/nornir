"""Public contracts added by feature 004; design artifact, not installed implementation.

Signatures only, checked with mypy. The generic run objects of spec 003 are restated as
generic Protocols to show their new type parameter; the classes keep their names and
modules. Each docstring names the module that will hold the class. Behaviour is specified
in ../spec.md and ../research.md; entry points and errors are in entry-points.md and
errors.md.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Literal, Protocol, overload

from nornir.core.inventory import Host
from nornir.core.run import RunOptions
from nornir.core.task import AggregatedResult, PartialResult

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from typing_extensions import TypeVar

    T = TypeVar("T", default=Any)
else:
    from typing import TypeVar

    T = TypeVar("T")

InT = TypeVar("InT")
OutT = TypeVar("OutT")


# --- Generic run objects (nornir.core.task, nornir.core.run) -------------------------


class Result(Generic[T]):
    """Result of one task for one host. Module: nornir.core.task.

    Only the type parameter is new. ``Result`` with no parameter means ``Result[Any]``
    for the type checker (research R1). Constructor arguments are unchanged.
    """

    result: T
    changed: bool
    diff: str
    failed: bool
    exception: BaseException | None
    host: Host | None


class RunStream(Protocol[T]):
    """Attached run. Module: nornir.core.run. Returned by run_stream and run_operation.

    ``results()`` is new: before this feature, a stream had only ``__iter__``.
    """

    def __iter__(self) -> Iterator[PartialResult | Result[T]]:
        """Iterate over the events of the run."""

    def results(self) -> Iterator[Result[T]]:
        """Yield the final result of each host, in completion order; iterates the stream."""

    def cancel(self) -> None:
        """Cancel the run."""

    def result(self) -> AggregatedResult:
        """Return the aggregated result once the run is finished."""


class RunHandle(Protocol[T]):
    """Background run. Module: nornir.core.run. Returned by submit and submit_operation."""

    def results(self) -> Iterator[Result[T]]:
        """Yield the final result of each host, in completion order."""

    def events(self) -> Iterator[PartialResult | Result[T]]:
        """Yield partial results and final results as they happen."""

    def cancel(self) -> None:
        """Cancel the run."""

    def result(self, timeout: float | None = None) -> AggregatedResult:
        """Return the aggregated result once the run is finished."""


class AsyncRunStream(Protocol[T]):
    """Attached asyncio run. Module: nornir.core.run. Returned by astream, arun_operation.

    ``results()`` is new: before this feature, a stream had only ``__aiter__``.
    """

    def __aiter__(self) -> AsyncIterator[PartialResult | Result[T]]:
        """Iterate over the events of the run."""

    def results(self) -> AsyncGenerator[Result[T], None]:
        """Yield the final result of each host, in completion order; iterates the stream."""

    def cancel(self) -> None:
        """Cancel the run."""

    async def result(self) -> AggregatedResult:
        """Return the aggregated result once the run is finished."""


class AsyncRunHandle(Protocol[T]):
    """Background asyncio run. Module: nornir.core.run. Returned by asubmit_operation."""

    def results(self) -> AsyncIterator[Result[T]]:
        """Yield the final result of each host, in completion order."""

    def events(self) -> AsyncIterator[PartialResult | Result[T]]:
        """Yield partial results and final results as they happen."""

    def cancel(self) -> None:
        """Cancel the run."""

    async def result(self) -> AggregatedResult:
        """Return the aggregated result once the run is finished."""


# --- Operations (nornir.core.operations) ---------------------------------------------


class Operation(Generic[InT, OutT]):
    """A typed contract. Module: nornir.core.operations.

    Subclass with two classes as type arguments and set ``name``. ``input_model`` and
    ``output_model`` are filled from the type arguments when the subclass is defined, and
    the subclass is registered under ``name`` (FR-018, research R3, R11). A subclass
    without ``name`` is not registered.
    """

    name: ClassVar[str]
    input_model: ClassVar[type[Any]]
    output_model: ClassVar[type[Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Read the models from the type arguments and register the class under ``name``."""


Params = Callable[[Host], InT]
"""A per-host input factory, called when the host's task starts (FR-008)."""


@dataclass(frozen=True)
class RegistrationSource:
    """Where a registration came from (FR-017). Module: nornir.core.operations."""

    kind: Literal["entry_point", "call"]
    module: str
    qualname: str
    distribution: str | None = None
    entry_point: str | None = None


@dataclass(frozen=True)
class Registration:
    """One implementation of one Operation. Module: nornir.core.operations."""

    operation: str
    platform: str
    connection: str
    task: Callable[..., Any]
    kind: Literal["sync", "async"]
    source: RegistrationSource


@dataclass(frozen=True)
class OperationInfo:
    """One known Operation, as listed by OperationRegistry.operations() (FR-019)."""

    name: str
    operation: type[Operation[Any, Any]] | None
    input_model: type[Any] | None
    output_model: type[Any] | None
    implementations: tuple[Registration, ...]


class OperationRegistry:
    """Contracts and implementations of the process. Module: nornir.core.operations.

    Class-level state guarded by one lock. Entry points are loaded on the first call to
    ``get`` or ``operations`` (research R9).
    """

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
        """Register ``task`` for the key.

        Raises:
            ValueError: ``platform`` or ``connection`` is None or empty (FR-013)
            OperationAlreadyRegisteredError: a different task holds the key and
                ``replace`` is False (FR-016)

        """
        raise NotImplementedError

    @classmethod
    def deregister(cls, *, operation: str, platform: str, connection: str) -> None:
        """Remove the registration for the key, if any."""

    @classmethod
    def get(cls, operation: str, platform: str, connection: str) -> Registration:
        """Return the registration for the key.

        Raises:
            OperationNotRegisteredError: nothing holds the key

        """
        raise NotImplementedError

    @classmethod
    def contract(cls, name: str) -> type[Operation[Any, Any]]:
        """Return the Operation class defined under ``name``.

        Raises:
            OperationContractNotFoundError: no class defines ``name`` (FR-020)

        """
        raise NotImplementedError

    @classmethod
    def operations(cls) -> list[OperationInfo]:
        """List every known Operation without calling any task (FR-019)."""
        raise NotImplementedError

    @classmethod
    def load(cls) -> None:
        """Load both entry-point groups once; idempotent and thread-safe.

        Raises:
            OperationAlreadyRegisteredError: two entry points conflict (FR-016)
            OperationEntryPointError: a malformed entry-point name (FR-015a)

        """


# --- New Nornir methods (nornir.core.Nornir) -----------------------------------------


class NornirOperations(Protocol):
    """The four methods added to nornir.core.Nornir.

    Shared keyword arguments:

    - ``connection``: overrides ``config.core.operation_connection`` (FR-005);
    - ``raise_on_error``, ``on_good``, ``on_failed``, ``name``, ``run_options``: as in
      ``run_stream`` / ``submit`` of spec 003.

    Raises before the run, with no stream or handle returned:
    OperationInputError (static params), OperationConnectionNotSetError,
    OperationContractNotFoundError (unknown name), RunnerCapabilityError,
    RunnerNotSyncError / RunnerNotAsyncError, and the registry loading errors.
    """

    @overload
    def run_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Params[InT] | None = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> RunStream[OutT]: ...
    @overload
    def run_operation(
        self,
        operation: str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> RunStream[Any]: ...

    @overload
    def submit_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Params[InT] | None = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> RunHandle[OutT]: ...
    @overload
    def submit_operation(
        self,
        operation: str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> RunHandle[Any]: ...

    @overload
    def arun_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Params[InT] | None = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> AsyncRunStream[OutT]: ...
    @overload
    def arun_operation(
        self,
        operation: str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> AsyncRunStream[Any]: ...

    @overload
    async def asubmit_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Params[InT] | None = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> AsyncRunHandle[OutT]: ...
    @overload
    async def asubmit_operation(
        self,
        operation: str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> AsyncRunHandle[Any]: ...
