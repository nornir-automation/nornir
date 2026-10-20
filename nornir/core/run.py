"""Runs that are started in the background, consumed live, cancelled, or given deadlines.

:meth:`nornir.core.Nornir.submit` and :meth:`nornir.core.Nornir.run_stream` (and their
asynchronous counterparts) return the objects defined here. Runners that implement
:class:`nornir.core.plugins.runners.StreamingRunner` receive a :class:`RunContext`.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import math
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from nornir.core.exceptions import TaskCancelledError, TaskInterruptedError, TaskTimeoutError
from nornir.core.task import AggregatedResult, MultiResult, PartialResult, Result

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Generator, Iterator
    from types import TracebackType

    from nornir.core.inventory import Host
    from nornir.core.plugins.runners import AsyncStreamingRunner, StreamingRunner
    from nornir.core.task import Task

    Finalize = Callable[[AggregatedResult], BaseException | None]
    """Applies the end-of-run bookkeeping and returns the error ``result()`` raises."""

logger = logging.getLogger(__name__)

RunEvent = PartialResult | Result
"""An event of a run: a partial result, or the final top-level result of one host."""


def _validate_timeout(name: str, value: object) -> float | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value <= 0
    ):
        msg = f"{name} must be None or a positive finite number of seconds, got {value!r}"
        raise ValueError(msg)
    return float(value)


@dataclass(frozen=True)
class RunOptions:
    """Settings for one run, kept separate from the arguments passed to the task.

    Arguments:
        per_host_timeout: Seconds each host may run, counted from the moment it starts.
            ``None`` keeps the runner's value
        timeout: Seconds the whole run may take, counted from the moment it starts.
            ``None`` keeps the runner's value

    Raises:
        ValueError: a value is not ``None`` or a positive finite number

    """

    per_host_timeout: float | None = None
    timeout: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "per_host_timeout", _validate_timeout("per_host_timeout", self.per_host_timeout)
        )
        object.__setattr__(self, "timeout", _validate_timeout("timeout", self.timeout))

    @property
    def has_deadlines(self) -> bool:
        """Whether a per-host or a run deadline is set."""
        return self.per_host_timeout is not None or self.timeout is not None


def _merge_options(base: RunOptions, override: RunOptions | None) -> RunOptions:
    if override is None:
        return base
    return RunOptions(
        per_host_timeout=(
            override.per_host_timeout
            if override.per_host_timeout is not None
            else base.per_host_timeout
        ),
        timeout=override.timeout if override.timeout is not None else base.timeout,
    )


_Status = Literal["pending", "running", "recorded"]


class _HostState:
    """Per-host state of a run. The task copy running for the host holds a reference."""

    __slots__ = (
        "deadline",
        "delivered",
        "host",
        "interruption",
        "results",
        "run",
        "scope",
        "status",
        "task",
    )

    def __init__(self, run: RunContext, host: Host) -> None:
        self.run = run
        self.host = host
        self.status: _Status = "pending"
        self.task: Task | None = None
        self.deadline: float | None = None
        self.scope: Literal["host", "run"] = "run"
        self.interruption: TaskInterruptedError | None = None
        self.delivered = False
        self.results: MultiResult | None = None

    def is_recorded(self) -> bool:
        with self.run._lock:
            return self.status == "recorded"

    def check(self) -> None:
        interruption = self.pending_interruption()
        if interruption is not None:
            raise interruption

    def pending_interruption(self) -> TaskInterruptedError | None:
        return self.run._pending_interruption(self)

    def claim(self) -> tuple[bool, TaskInterruptedError | None]:
        return self.run._claim(self)

    def published(self, results: MultiResult) -> None:
        self.run._publish_final(self, results)

    def publish(self, partial: PartialResult) -> None:
        self.run._publish_partial(self, partial)


class RunContext:
    """State of one run, shared by the core and the runner.

    The core creates one for each run and passes it to the runner. It records each host
    exactly once, fires the processor events of hosts that are recorded without running,
    applies the deadlines and delivers events to handles and streams. The runner only
    decides when each host starts, through :meth:`start_host`, :meth:`step_host` or
    :meth:`astart_host`. Every method is safe to call from any thread.

    Arguments:
        task: The task of the run
        hosts: The selected hosts, in selection order
        options: Effective deadlines of the run

    """

    def __init__(self, task: Task, hosts: list[Host], options: RunOptions | None = None) -> None:
        self._task = task
        self._hosts = list(hosts)
        self._options = options if options is not None else RunOptions()
        self._lock = threading.Lock()
        self._changed = threading.Condition(self._lock)
        self._states = {host.name: _HostState(self, host) for host in self._hosts}
        self._completed: list[Result] = []
        self._latest: dict[str, PartialResult] = {}
        self._subscribers: list[Callable[[RunEvent | None], object]] = []
        self._change_callbacks: list[Callable[[], object]] = []
        self._cancel_callbacks: list[Callable[[], object]] = []
        self._cancelled = False
        self._published = 0
        self._closed = False
        timeout = self._options.timeout
        self._run_deadline = time.monotonic() + timeout if timeout is not None else None

    @property
    def task(self) -> Task:
        """The task of the run."""
        return self._task

    @property
    def hosts(self) -> list[Host]:
        """The selected hosts, in selection order."""
        return list(self._hosts)

    @property
    def options(self) -> RunOptions:
        """Effective options of the run: per-run values over the runner's values."""
        return self._options

    @property
    def cancelled(self) -> bool:
        """Whether :meth:`cancel` was called or the run deadline passed."""
        with self._lock:
            return self._cancelled

    @property
    def finished(self) -> bool:
        """Whether every selected host is recorded."""
        with self._lock:
            return self._finished_locked()

    def _finished_locked(self) -> bool:
        return self._published == len(self._hosts)

    def running_hosts(self) -> list[Host]:
        """Return the hosts whose task has started and is not recorded yet.

        Returns:
            The running hosts.

        """
        with self._lock:
            return [s.host for s in self._states.values() if s.status == "running"]

    def completed(self) -> list[Result]:
        """Return the final top-level result of each recorded host.

        Returns:
            The results, in completion order.

        """
        with self._lock:
            return list(self._completed)

    def aggregated(self) -> AggregatedResult:
        """Return the results of every host.

        Returns:
            The results, keyed by host name in selection order.

        Raises:
            RuntimeError: a host is not recorded yet

        """
        result = AggregatedResult(self._task.name)
        for host in self._hosts:
            results = self._states[host.name].results
            if results is None:
                msg = f"host {host.name!r} has not been recorded yet"
                raise RuntimeError(msg)
            result[host.name] = results
        return result

    def start_host(self, task: Task, host: Host) -> MultiResult:
        """Run ``task``, a fresh copy of the run's task, for ``host`` and record it.

        If the host is already recorded (cancelled, or the run deadline passed before it
        started), return that record without calling the task.

        Returns:
            The results recorded for ``host``.

        """
        steps = self.step_host(task, host)
        while True:
            try:
                next(steps)
            except StopIteration as stop:
                return cast("MultiResult", stop.value)

    def step_host(self, task: Task, host: Host) -> Generator[None, None, MultiResult]:
        """Run like :meth:`start_host`, yielding after each top-level partial result.

        Returns:
            The results recorded for ``host``, as the value of the generator.

        """
        state = self._states[host.name]
        if not self._try_start(state, task):
            return cast("MultiResult", state.results)
        task._host_state = state
        return (yield from task._start_steps(host))  # noqa: B901 - read through yield from

    async def astart_host(self, task: Task, host: Host) -> MultiResult:
        """Run the asynchronous ``task`` for ``host`` and record it.

        Returns:
            The results recorded for ``host``.

        """
        state = self._states[host.name]
        if not self._try_start(state, task):
            return cast("MultiResult", state.results)
        task._host_state = state
        return await task.astart(host)

    def cancel(self) -> None:
        """Cancel the run.

        Hosts that have not started are recorded at once with
        :class:`~nornir.core.exceptions.TaskCancelledError`. Running hosts are interrupted
        at their next checkpoint, or at once by an ``immediate`` runner. Safe to call from
        any thread, any number of times.
        """
        with self._lock:
            if self._cancelled:
                return
            self._cancelled = True
            for state in self._states.values():
                if state.status == "running" and state.interruption is None:
                    state.interruption = TaskCancelledError(state.host.name, self._task.name)
            unstarted = [
                self._record_unstarted_locked(
                    state, TaskCancelledError(state.host.name, self._task.name, started=False)
                )
                for state in self._states.values()
                if state.status == "pending"
            ]
            callbacks = list(self._cancel_callbacks)
            self._notify_locked()
        self._announce_unstarted(unstarted)
        for callback in callbacks:
            callback()

    def expire(self) -> list[Host]:
        """Record the hosts past their deadline.

        That is every running host past its own deadline, and every pending host once the
        run deadline has passed.

        Returns:
            The running hosts recorded by this call, so that an ``immediate`` runner can
            interrupt them.

        """
        now = time.monotonic()
        callbacks: list[Callable[[], object]] = []
        with self._lock:
            expired = [
                state
                for state in self._states.values()
                if state.status == "running"
                and state.deadline is not None
                and now >= state.deadline
            ]
            for state in expired:
                if state.interruption is None:
                    state.interruption = self._timeout_error(state, started=True)
                task = cast("Task", state.task)
                task.results.insert(0, self._interruption_result(task, state.interruption))
                state.status = "recorded"
                state.results = task.results
            unstarted: list[_HostState] = []
            if self._run_deadline is not None and now >= self._run_deadline:
                unstarted = [
                    self._record_unstarted_locked(state, self._run_timeout_error(state))
                    for state in self._states.values()
                    if state.status == "pending"
                ]
                if not self._cancelled:
                    self._cancelled = True
                    callbacks = list(self._cancel_callbacks)
            if expired or unstarted:
                self._notify_locked()
        for state in expired:
            task = cast("Task", state.task)
            results = cast("MultiResult", state.results)
            task.processors.task_instance_completed(task, state.host, results)
            self._publish_final(state, results)
        self._announce_unstarted(unstarted)
        for callback in callbacks:
            callback()
        return [state.host for state in expired]

    def next_deadline(self) -> float | None:
        """Return the earliest deadline still pending.

        Returns:
            A :func:`time.monotonic` value, or ``None`` if no deadline is pending.

        """
        with self._lock:
            deadlines = [
                state.deadline
                for state in self._states.values()
                if state.status == "running" and state.deadline is not None
            ]
            if self._run_deadline is not None and any(
                state.status == "pending" for state in self._states.values()
            ):
                deadlines.append(self._run_deadline)
            return min(deadlines, default=None)

    def seconds_to_next_deadline(self) -> float | None:
        """Return how long a coordinator may wait before calling :meth:`expire`.

        Returns:
            Seconds until the earliest pending deadline (0 if it has passed), or ``None``
            if no deadline is pending.

        """
        deadline = self.next_deadline()
        return None if deadline is None else max(0.0, deadline - time.monotonic())

    def add_cancel_callback(self, callback: Callable[[], object]) -> None:
        """Call ``callback`` once, when the run is cancelled or its deadline passes.

        The callback runs on the thread that cancels the run, or at once if the run is
        already cancelled.
        """
        with self._lock:
            if not self._cancelled:
                self._cancel_callbacks.append(callback)
                return
        callback()

    def add_change_callback(self, callback: Callable[[], object]) -> None:
        """Call ``callback`` each time a host starts or is recorded, or the run is cancelled.

        The callback runs while the run's lock is held: it must return quickly and must
        not call back into the run. Use it to wake a coordinator.
        """
        with self._lock:
            self._change_callbacks.append(callback)

    def _remove_change_callback(self, callback: Callable[[], object]) -> None:
        with self._lock:
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)

    def _subscribe(self, subscriber: Callable[[RunEvent | None], object]) -> bool:
        with self._lock:
            if self._closed:
                return False
            self._subscribers.append(subscriber)
            return True

    def _unsubscribe(self, subscriber: Callable[[RunEvent | None], object]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def _close(self) -> None:
        """End every stream and ``results()`` loop: the run is finalized, or it failed."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._deliver_locked(None)
            self._notify_locked()

    def _notify_locked(self) -> None:
        self._changed.notify_all()
        for callback in self._change_callbacks:
            callback()

    def _deliver_locked(self, event: RunEvent | None) -> None:
        for subscriber in self._subscribers:
            subscriber(event)

    def _try_start(self, state: _HostState, task: Task) -> bool:
        with self._lock:
            if state.status != "pending":
                return False
            now = time.monotonic()
            if self._run_deadline is not None and now >= self._run_deadline:
                self._record_unstarted_locked(state, self._run_timeout_error(state))
                unstarted = [state]
            else:
                state.status = "running"
                state.task = task
                per_host = self._options.per_host_timeout
                host_deadline = now + per_host if per_host is not None else None
                if host_deadline is not None and (
                    self._run_deadline is None or host_deadline <= self._run_deadline
                ):
                    state.deadline, state.scope = host_deadline, "host"
                elif self._run_deadline is not None:
                    state.deadline, state.scope = self._run_deadline, "run"
                self._notify_locked()
                return True
        self._announce_unstarted(unstarted)
        return False

    def _pending_interruption(self, state: _HostState) -> TaskInterruptedError | None:
        with self._lock:
            if (
                state.interruption is None
                and state.status == "running"
                and state.deadline is not None
                and time.monotonic() >= state.deadline
            ):
                state.interruption = self._timeout_error(state, started=True)
            if state.interruption is None:
                return None
            state.delivered = True
            return state.interruption.fresh()

    def _claim(self, state: _HostState) -> tuple[bool, TaskInterruptedError | None]:
        with self._lock:
            if state.status == "recorded":
                return False, None
            state.status = "recorded"
            state.results = cast("Task", state.task).results
            return True, state.interruption if state.delivered else None

    def _publish_final(self, state: _HostState, results: MultiResult) -> None:
        with self._lock:
            self._completed.append(results[0])
            self._published += 1
            self._deliver_locked(results[0])
            self._notify_locked()

    def _publish_partial(self, state: _HostState, partial: PartialResult) -> None:
        with self._lock:
            if state.status == "recorded":
                return
            self._latest[state.host.name] = partial
            self._deliver_locked(partial)

    def _timeout_error(self, state: _HostState, started: bool) -> TaskTimeoutError:
        timeout = self._options.per_host_timeout if state.scope == "host" else self._options.timeout
        return TaskTimeoutError(
            state.host.name, self._task.name, cast("float", timeout), state.scope, started
        )

    def _run_timeout_error(self, state: _HostState) -> TaskTimeoutError:
        return TaskTimeoutError(
            state.host.name,
            self._task.name,
            cast("float", self._options.timeout),
            "run",
            started=False,
        )

    @staticmethod
    def _interruption_result(task: Task, interruption: TaskInterruptedError) -> Result:
        result = Result(task.host, result=str(interruption), failed=True, exception=interruption)
        result.name = task.name
        result.severity_level = logging.ERROR
        return result

    def _record_unstarted_locked(
        self, state: _HostState, interruption: TaskInterruptedError
    ) -> _HostState:
        task = self._task.copy()
        task.host = state.host
        task._host_state = state
        task.results.insert(0, self._interruption_result(task, interruption))
        state.task = task
        state.status = "recorded"
        state.interruption = interruption
        state.results = task.results
        return state

    def _announce_unstarted(self, states: list[_HostState]) -> None:
        for state in states:
            task = cast("Task", state.task)
            results = cast("MultiResult", state.results)
            task.processors.task_instance_started(task, state.host)
            task.processors.task_instance_completed(task, state.host, results)
            self._publish_final(state, results)


class RunHandle:
    """A run started in the background with :meth:`nornir.core.Nornir.submit`.

    The handle lives in the process that started the run. Any thread of that process can
    read it or cancel the run.
    """

    def __init__(self, run: RunContext) -> None:
        self._run = run
        self._id = uuid.uuid4().hex
        self._finished = threading.Event()
        self._result: AggregatedResult | None = None
        self._error: BaseException | None = None
        self._thread: threading.Thread | None = None

    @classmethod
    def _start(
        cls,
        runner: StreamingRunner,
        run: RunContext,
        finalize: Finalize,
        events: queue.SimpleQueue[RunEvent | None] | None = None,
    ) -> RunHandle:
        """Start ``run`` on a background thread, or finish it at once if no host is selected.

        Returns:
            The handle of the run.

        """
        handle = cls(run)
        if events is not None and not run._subscribe(events.put):
            events.put(None)
        if not run._hosts:
            handle._drive(runner, finalize)
        else:
            handle._thread = threading.Thread(
                target=handle._drive, args=(runner, finalize), name=f"nornir-run-{handle.id}"
            )
            handle._thread.start()
        return handle

    def _drive(self, runner: StreamingRunner, finalize: Finalize) -> None:
        run = self._run
        try:
            for _ in runner.execute(run._task, run._hosts, run):
                pass
            result = run.aggregated()
            self._finish(result, finalize(result))
        except BaseException as e:  # noqa: BLE001 - stored, then raised by result()
            self._fail(e)

    @property
    def id(self) -> str:
        """Identifier of the run, unique within the process."""
        return self._id

    @property
    def done(self) -> bool:
        """Whether every host is recorded and the run is finalized."""
        return self._finished.is_set()

    def results(self) -> Iterator[Result]:
        """Iterate over the final result of each host, in the order the hosts finish.

        Each call starts with the hosts that have already finished, then waits for the
        others. Failed hosts are yielded like any other; nothing is raised for them.
        Leaving the loop early does not cancel the run.

        Yields:
            The final top-level result of each host.

        """
        run = self._run
        index = 0
        while True:
            with run._changed:
                while index >= len(run._completed) and not run._closed:
                    run._changed.wait()
                if index >= len(run._completed):
                    return
                item = run._completed[index]
                index += 1
            yield item

    def events(self) -> Iterator[RunEvent]:
        """Iterate over the events produced from this call on.

        Events are :class:`~nornir.core.task.PartialResult` objects and the final
        :class:`~nornir.core.task.Result` of each host. Events produced before the call
        are not replayed: use :meth:`results` and :meth:`progress` for those.

        Returns:
            An iterator over the events.

        """
        events: queue.SimpleQueue[RunEvent | None] = queue.SimpleQueue()
        if not self._run._subscribe(events.put):
            return iter(())
        return _drain_queue(self._run, events)

    def progress(self) -> dict[str, PartialResult]:
        """Return the latest partial result of each host that reported one.

        Returns:
            The partial results, keyed by host name.

        """
        with self._run._lock:
            return dict(self._run._latest)

    def cancel(self) -> None:
        """Cancel the run. Safe from any thread, any number of times."""
        self._run.cancel()

    def result(self, timeout: float | None = None) -> AggregatedResult:
        """Wait for the run to finish and return its results, in selection order.

        Arguments:
            timeout: Seconds to wait. ``None`` waits until the run finishes

        Returns:
            The results of every selected host.

        Raises:
            TimeoutError: the run did not finish within ``timeout`` seconds
            nornir.core.exceptions.NornirExecutionError: ``raise_on_error`` applies and a
                host failed

        """
        if not self._finished.wait(timeout):
            msg = f"run {self._id} did not finish within {timeout} seconds"
            raise TimeoutError(msg)
        if self._error is not None:
            raise self._error
        return cast("AggregatedResult", self._result)

    def _finish(self, result: AggregatedResult, error: BaseException | None) -> None:
        self._result = result
        self._error = error
        self._finished.set()
        self._run._close()

    def _fail(self, error: BaseException) -> None:
        self._error = error
        self._finished.set()
        self._run._close()


def _drain_queue(
    run: RunContext, events: queue.SimpleQueue[RunEvent | None]
) -> Generator[RunEvent, None, None]:
    try:
        while (event := events.get()) is not None:
            yield event
    finally:
        run._unsubscribe(events.put)


class AsyncRunHandle:
    """A run started on the caller's event loop with :meth:`nornir.core.Nornir.asubmit`."""

    def __init__(self, run: RunContext) -> None:
        self._run = run
        self._id = uuid.uuid4().hex
        self._loop = asyncio.get_running_loop()
        self._finished: asyncio.Future[None] = self._loop.create_future()
        self._result: AggregatedResult | None = None
        self._error: BaseException | None = None
        self._driver: asyncio.Task[None] | None = None

    @classmethod
    def _start(
        cls,
        runner: AsyncStreamingRunner,
        run: RunContext,
        finalize: Finalize,
        events: asyncio.Queue[RunEvent | None] | None = None,
    ) -> tuple[AsyncRunHandle, Callable[[RunEvent | None], object] | None]:
        """Start ``run`` on the running loop, or finish it at once if no host is selected.

        Returns:
            The handle, and the subscriber feeding ``events`` (``None`` without events).

        """
        handle = cls(run)
        put = None
        if events is not None:
            put = _threadsafe_put(handle._loop, events)
            if not run._subscribe(put):
                events.put_nowait(None)
        if not run._hosts:
            result = run.aggregated()
            handle._finish(result, finalize(result))
        else:
            handle._driver = handle._loop.create_task(handle._drive(runner, finalize))
        return handle, put

    async def _drive(self, runner: AsyncStreamingRunner, finalize: Finalize) -> None:
        run = self._run
        try:
            await runner.aexecute(run._task, run._hosts, run)
            result = run.aggregated()
            self._finish(result, finalize(result))
        except BaseException as e:  # noqa: BLE001 - stored, then raised by result()
            self._fail(e)

    @property
    def id(self) -> str:
        """Identifier of the run, unique within the process."""
        return self._id

    @property
    def done(self) -> bool:
        """Whether every host is recorded and the run is finalized."""
        return self._finished.done()

    async def results(self) -> AsyncIterator[Result]:
        """Iterate over the final result of each host, in the order the hosts finish.

        Each call starts with the hosts that have already finished. Leaving the loop
        early does not cancel the run.

        Yields:
            The final top-level result of each host.

        """
        run = self._run
        changed = asyncio.Event()
        wake = functools.partial(self._loop.call_soon_threadsafe, changed.set)
        run.add_change_callback(wake)
        index = 0
        try:
            while True:
                changed.clear()
                with run._lock:
                    if index < len(run._completed):
                        item: Result | None = run._completed[index]
                        index += 1
                    elif run._closed:
                        return
                    else:
                        item = None
                if item is not None:
                    yield item
                else:
                    await changed.wait()
        finally:
            run._remove_change_callback(wake)

    def events(self) -> AsyncIterator[RunEvent]:
        """Iterate over the events produced from this call on.

        Returns:
            An asynchronous iterator over the events.

        """
        events: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        put = _threadsafe_put(self._loop, events)
        subscribed = self._run._subscribe(put)
        return _adrain_queue(self._run, events, put, subscribed)

    def progress(self) -> dict[str, PartialResult]:
        """Return the latest partial result of each host that reported one.

        Returns:
            The partial results, keyed by host name.

        """
        with self._run._lock:
            return dict(self._run._latest)

    def cancel(self) -> None:
        """Cancel the run. Safe from any thread, any number of times."""
        self._run.cancel()

    async def result(self) -> AggregatedResult:
        """Wait for the run to finish and return its results, in selection order.

        Cancelling the coroutine that awaits this method stops the waiting only; the run
        continues.

        Returns:
            The results of every selected host.

        Raises:
            nornir.core.exceptions.NornirExecutionError: ``raise_on_error`` applies and a
                host failed

        """
        await asyncio.shield(self._finished)
        if self._error is not None:
            raise self._error
        return cast("AggregatedResult", self._result)

    def _finish(self, result: AggregatedResult, error: BaseException | None) -> None:
        self._result = result
        self._error = error
        if not self._finished.done():
            self._finished.set_result(None)
        self._run._close()

    def _fail(self, error: BaseException) -> None:
        self._error = error
        if not self._finished.done():
            self._finished.set_result(None)
        self._run._close()


def _threadsafe_put(
    loop: asyncio.AbstractEventLoop, events: asyncio.Queue[RunEvent | None]
) -> Callable[[RunEvent | None], object]:
    """Return a subscriber that puts events on ``events`` from any thread.

    Returns:
        The subscriber.

    """

    def put(event: RunEvent | None) -> None:
        loop.call_soon_threadsafe(events.put_nowait, event)

    return put


async def _adrain_queue(
    run: RunContext,
    events: asyncio.Queue[RunEvent | None],
    put: Callable[[RunEvent | None], object],
    subscribed: bool,
) -> AsyncIterator[RunEvent]:
    if not subscribed:
        return
    try:
        while (event := await events.get()) is not None:
            yield event
    finally:
        run._unsubscribe(put)


class RunStream:
    """A run consumed live with :meth:`nornir.core.Nornir.run_stream`.

    Iterating over it yields the :class:`~nornir.core.task.PartialResult` objects and the
    final :class:`~nornir.core.task.Result` of each host, from the start of the run.
    Leaving the loop before the end (``break``, or an exception in the loop body) cancels
    the run, as does leaving a ``with`` block. A stream can be iterated once.
    """

    def __init__(
        self,
        run: RunContext,
        events: queue.SimpleQueue[RunEvent | None],
        handle: RunHandle | None = None,
        steps: Callable[[], Iterator[None]] | None = None,
        finalize: Callable[[], tuple[AggregatedResult, BaseException | None]] | None = None,
    ) -> None:
        self._run = run
        self._events = events
        self._handle = handle
        self._make_steps = steps
        self._finalize = finalize
        self._steps: Iterator[None] | None = None
        self._iterated = False
        self._ended = False
        self._result: AggregatedResult | None = None
        self._error: BaseException | None = None

    @classmethod
    def _start(cls, runner: StreamingRunner, run: RunContext, finalize: Finalize) -> RunStream:
        """Start ``run`` in the background, or prepare it to run on the caller's thread.

        Returns:
            The stream of the run.

        """
        events: queue.SimpleQueue[RunEvent | None] = queue.SimpleQueue()
        if runner.supports_background:
            return cls(run, events, handle=RunHandle._start(runner, run, finalize, events))
        run._subscribe(events.put)

        def steps() -> Iterator[None]:
            return runner.execute(run._task, run._hosts, run)

        def finish() -> tuple[AggregatedResult, BaseException | None]:
            result = run.aggregated()
            return result, finalize(result)

        return cls(run, events, steps=steps, finalize=finish)

    def __iter__(self) -> Iterator[RunEvent]:
        if self._iterated:
            msg = "a run stream can be iterated only once"
            raise RuntimeError(msg)
        self._iterated = True
        if self._handle is not None:
            return self._iterate_background()
        return self._iterate_foreground()

    def __enter__(self) -> RunStream:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._handle is not None:
            if not self._handle.done:
                self._handle.cancel()
            self._run._unsubscribe(self._events.put)
        elif not self._ended:
            self._run.cancel()
            self._run_to_end()

    def cancel(self) -> None:
        """Cancel the run."""
        self._run.cancel()

    def result(self) -> AggregatedResult:
        """Return the results of every host once the run has ended.

        On a runner that runs tasks on the caller's thread, this runs any remaining host
        first.

        Returns:
            The results of every selected host, in selection order.

        Raises:
            nornir.core.exceptions.NornirExecutionError: ``raise_on_error`` applies and a
                host failed

        """
        if self._handle is not None:
            return self._handle.result()
        self._run_to_end()
        if self._error is not None:
            raise self._error
        return cast("AggregatedResult", self._result)

    def _iterate_background(self) -> Generator[RunEvent, None, None]:
        handle = cast("RunHandle", self._handle)
        try:
            while (event := self._events.get()) is not None:
                yield event
        except GeneratorExit:
            handle.cancel()
            raise
        finally:
            self._run._unsubscribe(self._events.put)

    def _get_steps(self) -> Iterator[None]:
        if self._steps is None:
            self._steps = cast("Callable[[], Iterator[None]]", self._make_steps)()
        return self._steps

    def _flush(self) -> Generator[RunEvent, None, None]:
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                return
            if event is not None:
                yield event

    def _iterate_foreground(self) -> Generator[RunEvent, None, None]:
        try:
            for _ in self._get_steps():
                yield from self._flush()
            yield from self._flush()
            self._end()
        except GeneratorExit:
            self._run.cancel()
            self._run_to_end()
            raise

    def _run_to_end(self) -> None:
        if self._ended:
            return
        for _ in self._get_steps():
            pass
        self._end()

    def _end(self) -> None:
        if self._ended:
            return
        self._ended = True
        self._run._unsubscribe(self._events.put)
        self._result, self._error = cast(
            "Callable[[], tuple[AggregatedResult, BaseException | None]]", self._finalize
        )()
        self._run._close()


class AsyncRunStream:
    """A run consumed live on the event loop with :meth:`nornir.core.Nornir.astream`.

    Used with ``async for``. Leaving the loop before the end cancels the run, as does
    leaving an ``async with`` block. A stream can be iterated once.
    """

    def __init__(
        self,
        handle: AsyncRunHandle,
        events: asyncio.Queue[RunEvent | None],
        put: Callable[[RunEvent | None], object],
    ) -> None:
        self._handle = handle
        self._events = events
        self._put = put
        self._iterated = False

    @classmethod
    def _start(
        cls, runner: AsyncStreamingRunner, run: RunContext, finalize: Finalize
    ) -> AsyncRunStream:
        """Start ``run`` on the running loop, subscribed from its first event.

        Returns:
            The stream of the run.

        """
        events: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        handle, put = AsyncRunHandle._start(runner, run, finalize, events)
        return cls(handle, events, cast("Callable[[RunEvent | None], object]", put))

    def __aiter__(self) -> AsyncIterator[RunEvent]:
        if self._iterated:
            msg = "a run stream can be iterated only once"
            raise RuntimeError(msg)
        self._iterated = True
        return _AsyncStreamIterator(self._handle, self._events, self._put)

    async def __aenter__(self) -> AsyncRunStream:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if not self._handle.done:
            self._handle.cancel()

    def cancel(self) -> None:
        """Cancel the run."""
        self._handle.cancel()

    async def result(self) -> AggregatedResult:
        """Wait for the run to end and return the results of every host.

        Returns:
            The results of every selected host, in selection order.

        """
        return await self._handle.result()


class _AsyncStreamIterator:
    """Iterator of an :class:`AsyncRunStream`; cancels the run when dropped before the end."""

    def __init__(
        self,
        handle: AsyncRunHandle,
        events: asyncio.Queue[RunEvent | None],
        put: Callable[[RunEvent | None], object],
    ) -> None:
        self._handle = handle
        self._events = events
        self._put = put
        self._ended = False

    def __aiter__(self) -> _AsyncStreamIterator:
        return self

    async def __anext__(self) -> RunEvent:
        if self._ended:
            raise StopAsyncIteration
        event = await self._events.get()
        if event is None:
            self._end()
            raise StopAsyncIteration
        return event

    def _end(self) -> None:
        self._ended = True
        self._handle._run._unsubscribe(self._put)

    def __del__(self) -> None:
        if not self._ended:
            self._end()
            self._handle.cancel()
