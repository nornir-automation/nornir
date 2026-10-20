from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest

from nornir.core.exceptions import (
    AsyncTaskOnSyncRunError,
    RunnerCapabilityError,
    RunnerNotAsyncError,
    RunnerNotSyncError,
    SyncTaskOnAsyncRunError,
)
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from nornir.plugins.runners import AsyncioRunner, SerialRunner, ThreadedRunner
from tests.core.run_helpers import EventLog, asteps_task, make_nornir, steps_task

if TYPE_CHECKING:
    from nornir.core.inventory import Host
    from nornir.core.plugins.runners import AsyncStreamingRunner, StreamingRunner


class LegacyRunner:
    """Runner written against today's RunnerPlugin protocol only."""

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        result = AggregatedResult(task.name)
        for host in hosts:
            result[host.name] = task.copy().start(host)
        return result


class LegacyProcessor:
    """Processor implementing only the six existing hooks."""

    def __init__(self) -> None:
        self.calls = 0

    def task_started(self, task: Task) -> None:
        self.calls += 1

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.calls += 1

    def task_instance_started(self, task: Task, host: Host) -> None:
        self.calls += 1

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.calls += 1

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        self.calls += 1

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.calls += 1


def test_in_tree_runners_satisfy_the_streaming_protocols() -> None:
    serial: StreamingRunner = SerialRunner()
    threaded: StreamingRunner = ThreadedRunner()
    asyncio_runner: AsyncStreamingRunner = AsyncioRunner()
    assert (serial.cancellation_depth, serial.supports_background) == ("checkpoint", False)
    assert (threaded.cancellation_depth, threaded.supports_background) == ("checkpoint", True)
    assert asyncio_runner.cancellation_depth == "immediate"


def test_legacy_runner_and_processor_still_work_with_run() -> None:
    def task(task: Task) -> Result:
        task.checkpoint()
        return Result(host=task.host, result=task.host.name)

    processor = LegacyProcessor()
    nr = make_nornir(LegacyRunner(), 2, [processor])
    result = nr.run(task)
    assert {name: r[0].result for name, r in result.items()} == {"h000": "h000", "h001": "h001"}
    assert processor.calls == 6


class LegacyAsyncRunner:
    """Asynchronous runner written against AsyncRunnerPlugin only."""

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        raise NotImplementedError

    async def arun(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        result = AggregatedResult(task.name)
        for host in hosts:
            result[host.name] = await task.copy().astart(host)
        return result


async def agen_task(task: Task) -> Any:
    await asyncio.sleep(0)
    yield Result(host=task.host)


def gen_task(task: Task) -> Any:
    yield Result(host=task.host)


@pytest.mark.parametrize(
    ("runner", "entry_point", "task", "error"),
    [
        (ThreadedRunner(), "submit", asteps_task, AsyncTaskOnSyncRunError),
        (ThreadedRunner(), "run_stream", asteps_task, AsyncTaskOnSyncRunError),
        (ThreadedRunner(), "submit", agen_task, AsyncTaskOnSyncRunError),
        (AsyncioRunner(), "submit", steps_task, RunnerNotSyncError),
        (AsyncioRunner(), "run_stream", steps_task, RunnerNotSyncError),
        (LegacyRunner(), "submit", steps_task, RunnerCapabilityError),
        (LegacyRunner(), "run_stream", steps_task, RunnerCapabilityError),
    ],
)
def test_sync_entry_points_reject_before_any_event(
    runner: Any, entry_point: str, task: Any, error: type[Exception]
) -> None:
    log = EventLog()
    nr = make_nornir(runner, 2, [log])
    with pytest.raises(error):
        getattr(nr, entry_point)(task=task)
    assert log.hooks() == []


@pytest.mark.parametrize(
    ("runner", "entry_point", "task", "error"),
    [
        (AsyncioRunner(), "asubmit", steps_task, SyncTaskOnAsyncRunError),
        (AsyncioRunner(), "astream", gen_task, SyncTaskOnAsyncRunError),
        (ThreadedRunner(), "asubmit", asteps_task, RunnerNotAsyncError),
        (SerialRunner(), "astream", asteps_task, RunnerNotAsyncError),
        (LegacyAsyncRunner(), "asubmit", asteps_task, RunnerCapabilityError),
    ],
)
def test_async_entry_points_reject_before_any_event(
    runner: Any, entry_point: str, task: Any, error: type[Exception]
) -> None:
    async def scenario() -> None:
        log = EventLog()
        nr = make_nornir(runner, 2, [log])
        call = getattr(nr, entry_point)
        if entry_point == "asubmit":
            with pytest.raises(error):
                await call(task=task)
        else:
            with pytest.raises(error):
                call(task=task)
        assert log.hooks() == []

    asyncio.run(scenario())


def test_legacy_runner_error_message_names_the_protocol() -> None:
    nr = make_nornir(LegacyRunner(), 1)
    with pytest.raises(RunnerCapabilityError, match="Implement StreamingRunner"):
        nr.run_stream(task=steps_task)
