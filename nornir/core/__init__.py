from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Any, TypeGuard, TypeVar, get_args, overload

from nornir.core.configuration import Config
from nornir.core.exceptions import (
    AsyncTaskOnSyncRunError,
    NornirExecutionError,
    OperationConnectionNotSetError,
    PluginNotRegistered,
    RunnerCapabilityError,
    RunnerNotAsyncError,
    RunnerNotSyncError,
    SyncTaskOnAsyncRunError,
)
from nornir.core.inventory import Inventory
from nornir.core.operations import (
    Operation,
    OperationRegistry,
    _build_input,
    _is_per_host,
    _not_resolved,
    _OperationTask,
)
from nornir.core.plugins.runners import (
    AsyncRunnerPlugin,
    AsyncStreamingRunner,
    CancellationDepth,
    RunnerPlugin,
    StreamingRunner,
)
from nornir.core.processor import Processor, Processors
from nornir.core.run import (
    AsyncRunHandle,
    AsyncRunStream,
    RunContext,
    RunHandle,
    RunOptions,
    RunStream,
    _merge_options,
)
from nornir.core.state import GlobalState
from nornir.core.task import AggregatedResult, Task, _get_task_name, _is_async_task

if TYPE_CHECKING:
    import builtins
    import types
    from collections.abc import AsyncGenerator, Callable, Coroutine, Generator, Mapping

    from nornir.core.inventory import Host

logger = logging.getLogger(__name__)

InT = TypeVar("InT")
OutT = TypeVar("OutT")


def _is_async_runner(runner: RunnerPlugin) -> TypeGuard[AsyncRunnerPlugin]:
    """Return whether a runner structurally provides native asynchronous dispatch.

    Returns:
        Whether ``runner.arun`` is a native coroutine method.

    """
    return inspect.iscoroutinefunction(getattr(runner, "arun", None))


_DEPTHS = frozenset(get_args(CancellationDepth))


def _is_streaming_runner(runner: RunnerPlugin) -> TypeGuard[StreamingRunner]:
    """Return whether a runner structurally implements :class:`StreamingRunner`.

    Returns:
        Whether the runner has ``execute``, a valid ``cancellation_depth``, a boolean
        ``supports_background`` and ``run_options``.

    """
    return (
        callable(getattr(runner, "execute", None))
        and getattr(runner, "cancellation_depth", None) in _DEPTHS
        and isinstance(getattr(runner, "supports_background", None), bool)
        and isinstance(getattr(runner, "run_options", None), RunOptions)
    )


def _is_async_streaming_runner(runner: RunnerPlugin) -> TypeGuard[AsyncStreamingRunner]:
    """Return whether a runner structurally implements :class:`AsyncStreamingRunner`.

    Returns:
        Whether the runner has a native coroutine ``aexecute``, a valid
        ``cancellation_depth`` and ``run_options``.

    """
    return (
        inspect.iscoroutinefunction(getattr(runner, "aexecute", None))
        and getattr(runner, "cancellation_depth", None) in _DEPTHS
        and isinstance(getattr(runner, "run_options", None), RunOptions)
    )


class Nornir:  # noqa: PLR0904 - each entry point is public API: run, stream, submit, Operations
    """Main object to work with.

    It contains the inventory and it serves as task dispatcher.

    Arguments:
        inventory (:obj:`nornir.core.inventory.Inventory`): Inventory to work with
        data(GlobalState): shared data amongst different iterations of nornir
        dry_run(``bool``): Whether if we are testing the changes or not
        config (:obj:`nornir.core.configuration.Config`): Configuration object

    Attributes:
        inventory (:obj:`nornir.core.inventory.Inventory`): Inventory to work with
        data(:obj:`nornir.core.GlobalState`): shared data amongst different iterations of nornir
        dry_run(``bool``): Whether if we are testing the changes or not
        config (:obj:`nornir.core.configuration.Config`): Configuration parameters

    """

    def __init__(
        self,
        inventory: Inventory,
        config: Config | None = None,
        data: GlobalState | None = None,
        processors: Processors | None = None,
        runner: RunnerPlugin | None = None,
    ) -> None:
        self.data = data if data is not None else GlobalState()
        self.inventory = inventory
        self.config = config or Config()
        self.processors = processors or Processors()
        self._runner = runner

    def __enter__(self) -> Nornir:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: types.TracebackType | None = None,
    ) -> None:
        self.close_connections(on_good=True, on_failed=True)

    async def __aenter__(self) -> Nornir:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        await self.aclose_connections(on_good=True, on_failed=True)

    def with_processors(self, processors: list[Processor]) -> Nornir:
        """Return a copy of the object with the given processors assigned to it.

        The original object is left unmodified.

        Returns:
            :obj:`Nornir`: A copy of ``self`` with the given processors assigned.

        """
        return Nornir(**{**self._clone_parameters(), **{"processors": Processors(processors)}})

    def with_runner(self, runner: RunnerPlugin) -> Nornir:
        """Return a copy of the object with the given runner assigned to it.

        The original object is left unmodified.

        Returns:
            :obj:`Nornir`: A copy of ``self`` with the given runner assigned.

        """
        return Nornir(**{**self._clone_parameters(), **{"runner": runner}})

    def filter(self, *args: Any, **kwargs: Any) -> Nornir:
        """Return a copy of the object with a filtered inventory.

        See :py:meth:`nornir.core.inventory.Inventory.filter` for the accepted arguments.

        Returns:
            :obj:`Nornir`: A new object with same configuration as ``self`` but filtered inventory.

        """
        b = Nornir(**self._clone_parameters())
        b.inventory = self.inventory.filter(*args, **kwargs)
        return b

    def run(
        self,
        task: Callable[..., Any],
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        **kwargs: Any,
    ) -> AggregatedResult:
        """Run task over all the hosts in the inventory.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            raise_on_error (``bool``): Override raise_on_error behavior
            on_good(``bool``): Whether to run or not this task on hosts marked as good
            on_failed(``bool``): Whether to run or not this task on hosts marked as failed
            name (``str``): Name of the task, defaults to the name of the ``task`` callable
            **kwargs: additional argument to pass to ``task`` when calling it

        Returns:
            :obj:`nornir.core.task.AggregatedResult`: results of each execution

        Raises:
            nornir.core.exceptions.NornirExecutionError: if at least a task fails
              and self.config.core.raise_on_error is set to ``True``
            nornir.core.exceptions.AsyncTaskOnSyncRunError: if ``task`` is asynchronous

        """
        if _is_async_task(task):
            raise AsyncTaskOnSyncRunError(_get_task_name(task, name))
        run_task, run_on = self._prepare_run(task, name, kwargs, on_good, on_failed)
        result = self.runner.run(run_task, run_on)
        return self._finalize_run(run_task, result, raise_on_error)

    async def arun(
        self,
        task: Callable[..., Coroutine[Any, Any, Any] | AsyncGenerator[Any, None]],
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        **kwargs: Any,
    ) -> AggregatedResult:
        """Run an asynchronous task over selected hosts on the caller's event loop.

        Arguments:
            task: Coroutine function or asynchronous callable to run for each host
            raise_on_error: Override the configured ``raise_on_error`` behavior
            on_good: Whether to run on hosts not marked as failed
            on_failed: Whether to run on hosts marked as failed
            name: Task name, defaulting to the callable's name
            **kwargs: Additional arguments passed to ``task``

        Returns:
            Results from every selected host.

        Raises:
            nornir.core.exceptions.SyncTaskOnAsyncRunError: if ``task`` is synchronous
            nornir.core.exceptions.RunnerNotAsyncError: if the selected runner does not
                provide asynchronous dispatch
            nornir.core.exceptions.NornirExecutionError: if a task fails and effective
                ``raise_on_error`` is true

        """
        if not _is_async_task(task):
            raise SyncTaskOnAsyncRunError(_get_task_name(task, name))

        runner = self.runner
        if not _is_async_runner(runner):
            raise RunnerNotAsyncError(type(runner).__name__)

        run_task, run_on = self._prepare_run(task, name, kwargs, on_good, on_failed)
        result = await runner.arun(run_task, run_on)
        return self._finalize_run(run_task, result, raise_on_error)

    def _prepare_run(
        self,
        task: Callable[..., Any],
        name: str | None,
        kwargs: dict[str, Any],
        on_good: bool,
        on_failed: bool,
        run_task: Task | None = None,
    ) -> tuple[Task, list[Host]]:
        if run_task is None:
            run_task = Task(
                task,
                self,
                global_dry_run=self.data.dry_run,
                name=name,
                processors=self.processors,
                **kwargs,
            )
        self.processors.task_started(run_task)

        run_on = []
        if on_good:
            for hostname, host in self.inventory.hosts.items():
                if hostname not in self.data.failed_hosts:
                    run_on.append(host)
        if on_failed:
            for hostname, host in self.inventory.hosts.items():
                if hostname in self.data.failed_hosts:
                    run_on.append(host)

        num_hosts = len(run_on)
        if num_hosts:
            logger.info(
                "Running task %r with args %s on %d hosts",
                run_task.name,
                kwargs,
                num_hosts,
            )
        else:
            logger.warning("Task %r has not been run – 0 hosts selected", run_task.name)

        return run_task, run_on

    def _finalize_run(
        self,
        run_task: Task,
        result: AggregatedResult,
        raise_on_error: bool | None,
    ) -> AggregatedResult:
        error = self._complete_run(run_task, result, raise_on_error)
        if error is not None:
            raise error
        return result

    def _complete_run(
        self,
        run_task: Task,
        result: AggregatedResult,
        raise_on_error: bool | None,
    ) -> NornirExecutionError | None:
        """Apply the end-of-run bookkeeping, or return the error ``run()`` would raise.

        When ``raise_on_error`` applies and a host failed, the error is returned before
        ``task_completed`` fires, as ``run()`` has always done.

        Returns:
            The error to raise, or ``None``.

        """
        raise_on_error = (
            raise_on_error if raise_on_error is not None else self.config.core.raise_on_error
        )
        if raise_on_error:
            if result.failed:
                return NornirExecutionError(result)
        else:
            self.data.failed_hosts.update(result.failed_hosts.keys())

        self.processors.task_completed(run_task, result)
        return None

    def _sync_streaming_runner(
        self, task: Callable[..., Any], name: str | None, capability: str, check_task: bool = True
    ) -> StreamingRunner:
        if check_task and _is_async_task(task):
            raise AsyncTaskOnSyncRunError(_get_task_name(task, name))
        runner = self.runner
        if _is_streaming_runner(runner):
            return runner
        if _is_async_runner(runner) or _is_async_streaming_runner(runner):
            raise RunnerNotSyncError(type(runner).__name__)
        raise RunnerCapabilityError(type(runner).__name__, capability)

    def _async_streaming_runner(
        self, task: Callable[..., Any], name: str | None, capability: str, check_task: bool = True
    ) -> AsyncStreamingRunner:
        if check_task and not _is_async_task(task):
            raise SyncTaskOnAsyncRunError(_get_task_name(task, name))
        runner = self.runner
        if _is_async_streaming_runner(runner):
            return runner
        if _is_async_runner(runner):
            raise RunnerCapabilityError(type(runner).__name__, capability)
        raise RunnerNotAsyncError(type(runner).__name__)

    def _new_run(
        self,
        runner: StreamingRunner | AsyncStreamingRunner,
        task: Callable[..., Any],
        name: str | None,
        kwargs: dict[str, Any],
        selection: tuple[bool, bool],
        run_options: RunOptions | None,
        run_task: Task | None = None,
    ) -> RunContext:
        on_good, on_failed = selection
        run_task, run_on = self._prepare_run(task, name, kwargs, on_good, on_failed, run_task)
        return RunContext(run_task, run_on, _merge_options(runner.run_options, run_options))

    def _finalizer(
        self, run: RunContext, raise_on_error: bool | None
    ) -> Callable[[AggregatedResult], BaseException | None]:
        def finalize(result: AggregatedResult) -> BaseException | None:
            return self._complete_run(run.task, result, raise_on_error)

        return finalize

    def submit(
        self,
        task: Callable[..., Any],
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
        **kwargs: Any,
    ) -> RunHandle:
        """Start running a task over the hosts in the background and return at once.

        The runner must implement :class:`~nornir.core.plugins.runners.StreamingRunner`
        and support background runs, as ``ThreadedRunner`` does. Processors receive the
        same events as with :meth:`run`; ``task_started`` fires before this method returns.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            raise_on_error (``bool``): Override raise_on_error behavior. The error is raised
              by :meth:`nornir.core.run.RunHandle.result`
            on_good(``bool``): Whether to run or not this task on hosts marked as good
            on_failed(``bool``): Whether to run or not this task on hosts marked as failed
            name (``str``): Name of the task, defaults to the name of the ``task`` callable
            run_options: Deadlines of this run, overriding the runner's
            **kwargs: additional argument to pass to ``task`` when calling it

        Returns:
            :obj:`nornir.core.run.RunHandle`: The handle of the run.

        Raises:
            nornir.core.exceptions.AsyncTaskOnSyncRunError: ``task`` is asynchronous
            nornir.core.exceptions.RunnerNotSyncError: the runner is asynchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not support
                background runs

        """
        runner = self._sync_streaming_runner(task, name, "submit")
        if not runner.supports_background:
            raise RunnerCapabilityError(type(runner).__name__, "submit", background=True)
        run = self._new_run(runner, task, name, kwargs, (on_good, on_failed), run_options)
        return RunHandle._start(runner, run, self._finalizer(run, raise_on_error))

    def run_stream(
        self,
        task: Callable[..., Any],
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
        **kwargs: Any,
    ) -> RunStream:
        """Run a task over the hosts and iterate over its events as they happen.

        The stream yields :class:`~nornir.core.task.PartialResult` objects and the final
        :class:`~nornir.core.task.Result` of each host. Leaving the loop before the end
        cancels the run. On ``SerialRunner``, every task runs on the caller's thread while
        the loop runs.

        Arguments:
            task (``callable``): function or callable that will be run against each device in
              the inventory
            raise_on_error (``bool``): Override raise_on_error behavior. The error is raised
              by :meth:`nornir.core.run.RunStream.result`
            on_good(``bool``): Whether to run or not this task on hosts marked as good
            on_failed(``bool``): Whether to run or not this task on hosts marked as failed
            name (``str``): Name of the task, defaults to the name of the ``task`` callable
            run_options: Deadlines of this run, overriding the runner's
            **kwargs: additional argument to pass to ``task`` when calling it

        Returns:
            :obj:`nornir.core.run.RunStream`: The stream of the run.

        Raises:
            nornir.core.exceptions.AsyncTaskOnSyncRunError: ``task`` is asynchronous
            nornir.core.exceptions.RunnerNotSyncError: the runner is asynchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not implement
                streaming

        """
        runner = self._sync_streaming_runner(task, name, "run_stream")
        run = self._new_run(runner, task, name, kwargs, (on_good, on_failed), run_options)
        return RunStream._start(runner, run, self._finalizer(run, raise_on_error))

    async def asubmit(
        self,
        task: Callable[..., Coroutine[Any, Any, Any] | AsyncGenerator[Any, None]],
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
        **kwargs: Any,
    ) -> AsyncRunHandle:
        """Start running an asynchronous task on the caller's event loop and return at once.

        The runner must implement
        :class:`~nornir.core.plugins.runners.AsyncStreamingRunner`, as ``AsyncioRunner``
        does. ``task_started`` fires before this coroutine returns.

        Arguments:
            task: Coroutine function, async generator function, or asynchronous callable
                to run for each host
            raise_on_error: Override the configured ``raise_on_error`` behavior. The error
                is raised by :meth:`nornir.core.run.AsyncRunHandle.result`
            on_good: Whether to run on hosts not marked as failed
            on_failed: Whether to run on hosts marked as failed
            name: Task name, defaulting to the callable's name
            run_options: Deadlines of this run, overriding the runner's
            **kwargs: Additional arguments passed to ``task``

        Returns:
            :obj:`nornir.core.run.AsyncRunHandle`: The handle of the run.

        Raises:
            nornir.core.exceptions.SyncTaskOnAsyncRunError: ``task`` is synchronous
            nornir.core.exceptions.RunnerNotAsyncError: the runner is synchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not implement
                ``AsyncStreamingRunner``

        """
        runner = self._async_streaming_runner(task, name, "asubmit")
        run = self._new_run(runner, task, name, kwargs, (on_good, on_failed), run_options)
        handle, _ = AsyncRunHandle._start(runner, run, self._finalizer(run, raise_on_error))
        return handle

    def astream(
        self,
        task: Callable[..., Coroutine[Any, Any, Any] | AsyncGenerator[Any, None]],
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
        **kwargs: Any,
    ) -> AsyncRunStream:
        """Run an asynchronous task on the caller's event loop and iterate over its events.

        Use it with ``async for``, from inside a coroutine; no ``await`` is needed. Leaving
        the loop before the end cancels the run.

        Arguments:
            task: Coroutine function, async generator function, or asynchronous callable
                to run for each host
            raise_on_error: Override the configured ``raise_on_error`` behavior
            on_good: Whether to run on hosts not marked as failed
            on_failed: Whether to run on hosts marked as failed
            name: Task name, defaulting to the callable's name
            run_options: Deadlines of this run, overriding the runner's
            **kwargs: Additional arguments passed to ``task``

        Returns:
            :obj:`nornir.core.run.AsyncRunStream`: The stream of the run.

        Raises:
            nornir.core.exceptions.SyncTaskOnAsyncRunError: ``task`` is synchronous
            nornir.core.exceptions.RunnerNotAsyncError: the runner is synchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not implement
                ``AsyncStreamingRunner``

        """
        runner = self._async_streaming_runner(task, name, "astream")
        asyncio.get_running_loop()  # fail before task_started when called outside a loop
        run = self._new_run(runner, task, name, kwargs, (on_good, on_failed), run_options)
        return AsyncRunStream._start(runner, run, self._finalizer(run, raise_on_error))

    def _operation_task(
        self,
        operation: type[Operation[Any, Any]] | str,
        params: Any,
        connection: str | None,
        name: str | None,
    ) -> _OperationTask:
        """Resolve the Operation, its connection and a static input, before the run.

        Returns:
            The task to run; it selects the implementation when each host starts.

        Raises:
            nornir.core.exceptions.OperationContractNotFoundError: no Operation has the
                given name
            nornir.core.exceptions.OperationConnectionNotSetError: no connection is given
                or configured
            nornir.core.exceptions.OperationInputError: the static input is invalid

        """
        OperationRegistry.load()
        contract = (
            OperationRegistry.contract(operation) if isinstance(operation, str) else operation
        )
        connection = connection or self.config.core.operation_connection
        if not connection:
            raise OperationConnectionNotSetError(contract.name)
        per_host = _is_per_host(params, contract.input_model)
        if not per_host:
            params = _build_input(contract.name, contract.input_model, params)
        return _OperationTask(
            contract,
            connection,
            params,
            per_host,
            self,
            global_dry_run=self.data.dry_run,
            processors=self.processors,
            name=name,
        )

    @overload
    def run_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Callable[[Host], InT] | None = None,
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
    def run_operation(
        self,
        operation: type[Operation[Any, Any]] | str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> RunStream[Any]:
        """Run an Operation over the hosts and iterate over its events as they happen.

        Each host runs the task registered for the Operation, the host's platform and the
        connection, and its result holds an instance of the Operation's output model. A
        host for which no task is registered, or whose task returns another type, fails
        on its own; the other hosts continue. The stream behaves as the one of
        :meth:`run_stream`, so it works on ``SerialRunner`` too.

        Arguments:
            operation: The Operation class, which types the results, or its name
            params: The input, given to the task as its ``params`` argument: an instance
                of the input model, a mapping of its fields, ``None`` for the model's
                defaults, or a callable that receives the host and returns its input
            connection: Name of the connection, overriding ``core.operation_connection``
            raise_on_error: Override raise_on_error behavior. The error is raised by
                :meth:`nornir.core.run.RunStream.result`
            on_good: Whether to run on hosts not marked as failed
            on_failed: Whether to run on hosts marked as failed
            name: Name of the task, defaults to the name of the Operation
            run_options: Deadlines of this run, overriding the runner's

        Returns:
            :obj:`nornir.core.run.RunStream`: The stream of the run.

        Raises:
            nornir.core.exceptions.OperationContractNotFoundError: no Operation has the
                given name
            nornir.core.exceptions.OperationConnectionNotSetError: no connection is given
                or configured
            nornir.core.exceptions.OperationInputError: the static input is invalid
            nornir.core.exceptions.RunnerNotSyncError: the runner is asynchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not implement
                streaming

        """
        run_task = self._operation_task(operation, params, connection, name)
        runner = self._sync_streaming_runner(_not_resolved, name, "run_operation", check_task=False)
        run = self._new_run(
            runner, _not_resolved, name, {}, (on_good, on_failed), run_options, run_task
        )
        return RunStream._start(runner, run, self._finalizer(run, raise_on_error))

    @overload
    def submit_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Callable[[Host], InT] | None = None,
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
    def submit_operation(
        self,
        operation: type[Operation[Any, Any]] | str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> RunHandle[Any]:
        """Start running an Operation over the hosts in the background and return at once.

        The arguments and the selection of each host's task are those of
        :meth:`run_operation`; the runner must support background runs, as for
        :meth:`submit`.

        Returns:
            :obj:`nornir.core.run.RunHandle`: The handle of the run.

        Raises:
            nornir.core.exceptions.OperationContractNotFoundError: no Operation has the
                given name
            nornir.core.exceptions.OperationConnectionNotSetError: no connection is given
                or configured
            nornir.core.exceptions.OperationInputError: the static input is invalid
            nornir.core.exceptions.RunnerNotSyncError: the runner is asynchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not support
                background runs

        """
        run_task = self._operation_task(operation, params, connection, name)
        runner = self._sync_streaming_runner(
            _not_resolved, name, "submit_operation", check_task=False
        )
        if not runner.supports_background:
            raise RunnerCapabilityError(type(runner).__name__, "submit_operation", background=True)
        run = self._new_run(
            runner, _not_resolved, name, {}, (on_good, on_failed), run_options, run_task
        )
        return RunHandle._start(runner, run, self._finalizer(run, raise_on_error))

    @overload
    def arun_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Callable[[Host], InT] | None = None,
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
    def arun_operation(
        self,
        operation: type[Operation[Any, Any]] | str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> AsyncRunStream[Any]:
        """Run an Operation on the caller's event loop and iterate over its events.

        The asynchronous counterpart of :meth:`run_operation`, used as :meth:`astream`
        is: with ``async for``, from inside a coroutine. Each host's task must be an
        ``async def``; a host whose task is synchronous fails with
        :class:`~nornir.core.exceptions.SyncTaskOnAsyncRunError`.

        Returns:
            :obj:`nornir.core.run.AsyncRunStream`: The stream of the run.

        Raises:
            nornir.core.exceptions.OperationContractNotFoundError: no Operation has the
                given name
            nornir.core.exceptions.OperationConnectionNotSetError: no connection is given
                or configured
            nornir.core.exceptions.OperationInputError: the static input is invalid
            nornir.core.exceptions.RunnerNotAsyncError: the runner is synchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not implement
                ``AsyncStreamingRunner``

        """
        run_task = self._operation_task(operation, params, connection, name)
        runner = self._async_streaming_runner(
            _not_resolved, name, "arun_operation", check_task=False
        )
        asyncio.get_running_loop()  # fail before task_started when called outside a loop
        run = self._new_run(
            runner, _not_resolved, name, {}, (on_good, on_failed), run_options, run_task
        )
        return AsyncRunStream._start(runner, run, self._finalizer(run, raise_on_error))

    @overload
    async def asubmit_operation(
        self,
        operation: type[Operation[InT, OutT]],
        params: InT | Mapping[str, Any] | Callable[[Host], InT] | None = None,
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
    async def asubmit_operation(
        self,
        operation: type[Operation[Any, Any]] | str,
        params: Any = None,
        *,
        connection: str | None = None,
        raise_on_error: bool | None = None,
        on_good: bool = True,
        on_failed: bool = False,
        name: str | None = None,
        run_options: RunOptions | None = None,
    ) -> AsyncRunHandle[Any]:
        """Start running an Operation on the caller's event loop and return at once.

        The asynchronous counterpart of :meth:`submit_operation`, with the rules of
        :meth:`asubmit`. Each host's task must be an ``async def``.

        Returns:
            :obj:`nornir.core.run.AsyncRunHandle`: The handle of the run.

        Raises:
            nornir.core.exceptions.OperationContractNotFoundError: no Operation has the
                given name
            nornir.core.exceptions.OperationConnectionNotSetError: no connection is given
                or configured
            nornir.core.exceptions.OperationInputError: the static input is invalid
            nornir.core.exceptions.RunnerNotAsyncError: the runner is synchronous only
            nornir.core.exceptions.RunnerCapabilityError: the runner does not implement
                ``AsyncStreamingRunner``

        """
        run_task = self._operation_task(operation, params, connection, name)
        runner = self._async_streaming_runner(
            _not_resolved, name, "asubmit_operation", check_task=False
        )
        run = self._new_run(
            runner, _not_resolved, name, {}, (on_good, on_failed), run_options, run_task
        )
        handle, _ = AsyncRunHandle._start(runner, run, self._finalizer(run, raise_on_error))
        return handle

    def dict(self) -> dict[str, Any]:
        """Return a dictionary representing the object.

        Returns:
            The ``data`` and ``inventory`` attributes serialized as dictionaries.

        """
        return {"data": self.data.dict(), "inventory": self.inventory.dict()}

    def close_connections(self, on_good: bool = True, on_failed: bool = False) -> None:
        """Close all the connections open on the hosts of the inventory.

        The connections are closed by running a task, so the call goes through the
        runner and the processors see it like any other task. Using the object as a
        context manager closes the connections of every host on exit, failed ones
        included.

        Arguments:
            on_good(``bool``): Whether to close the connections of the hosts marked as good
            on_failed(``bool``): Whether to close the connections of the hosts marked as failed

        """

        def close_connections_task(task: Task) -> None:
            task.host.close_connections()

        self.run(task=close_connections_task, on_good=on_good, on_failed=on_failed)

    async def aclose_connections(
        self,
        on_good: bool = True,
        on_failed: bool = False,
    ) -> None:
        """Close connections on selected hosts through the asynchronous runner.

        Failures follow normal task bookkeeping. Retry failed hosts with
        ``on_failed=True`` or close them directly through their Host objects.

        Arguments:
            on_good: Whether to close connections on hosts not marked as failed.
            on_failed: Whether to close connections on hosts marked as failed.

        """

        async def close_connections_task(task: Task) -> None:
            await task.host.aclose_connections()

        await self.arun(
            task=close_connections_task,
            on_good=on_good,
            on_failed=on_failed,
        )

    @property
    def runner(self) -> RunnerPlugin:
        """The runner this object dispatches its tasks with.

        Returns:
            :obj:`nornir.core.plugins.runners.RunnerPlugin`: The runner assigned to ``self``.

        Raises:
            nornir.core.exceptions.PluginNotRegistered: no runner was assigned. Objects
                built by :obj:`nornir.InitNornir` always have one, so this is only
                reachable when constructing :obj:`Nornir` directly.

        """
        if self._runner:
            return self._runner

        raise PluginNotRegistered("Runner plugin not registered")

    def _clone_parameters(self) -> builtins.dict[str, Any]:
        return {
            "data": self.data,
            "inventory": self.inventory,
            "config": self.config,
            "processors": self.processors,
            "runner": self._runner,
        }

    @classmethod
    def get_validators(cls) -> Generator[Callable[[Nornir], Nornir], None, None]:
        """Yield the validators used to accept a :obj:`Nornir` as a field of a model.

        Yields:
            :py:meth:`validate`.

        """
        # Left over from the time nornir modelled its objects with pydantic. Nothing in
        # nornir calls it, and the name does not match the hook any released pydantic
        # looks for (__get_validators__ in v1, __get_pydantic_core_schema__ in v2), so
        # it has no effect on its own.
        yield cls.validate

    @classmethod
    def validate(cls, v: Nornir) -> Nornir:
        """Return ``v`` unchanged if it is a :obj:`Nornir` object.

        Returns:
            :obj:`Nornir`: The object that was passed in.

        Raises:
            ValueError: ``v`` is not an instance of this class.

        """
        # Counterpart of get_validators, and equally unused.
        if not isinstance(v, cls):
            raise ValueError(f"Nornir: Nornir expected not {type(v)}")
        return v
