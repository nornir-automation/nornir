from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any

import pytest

from nornir.core.exceptions import AsyncTaskOnSyncRunError, TaskCancelledError
from nornir.core.task import PartialResult, Result, Task
from nornir.plugins.runners import SerialRunner, ThreadedRunner
from tests.core.run_helpers import EventLog, make_nornir
from tests.core.test_run_contract import LegacyProcessor

if TYPE_CHECKING:
    from collections.abc import Generator

    from nornir.core.plugins.runners import RunnerPlugin


def upgrade(task: Task) -> Generator[PartialResult, None, Result]:
    yield PartialResult(host=task.host, result="uploading", progress=0.2)
    yield PartialResult(host=task.host, result="rebooting", progress=0.7)
    return Result(host=task.host, result="running new version", changed=True)


@pytest.mark.parametrize("runner", [SerialRunner(), ThreadedRunner()])
def test_stream_delivers_partials_then_the_final_result(runner: RunnerPlugin) -> None:
    nr = make_nornir(runner, 2)
    events = list(nr.run_stream(task=upgrade))
    for host in ("h000", "h001"):
        mine = [e for e in events if e.host and e.host.name == host]
        assert [type(e).__name__ for e in mine] == ["PartialResult", "PartialResult", "Result"]
        assert [e.result for e in mine] == ["uploading", "rebooting", "running new version"]
        assert mine[0].name == "upgrade"


def test_processor_receives_partials_under_plain_run() -> None:
    log = EventLog()
    legacy = LegacyProcessor()
    nr = make_nornir(ThreadedRunner(), 2, [log, legacy])
    result = nr.run(task=upgrade)
    assert sorted((p.host.name, p.result) for p in log.partials) == [
        ("h000", "rebooting"),
        ("h000", "uploading"),
        ("h001", "rebooting"),
        ("h001", "uploading"),
    ]
    assert legacy.calls == 6
    for multi in result.values():
        assert all(type(r) is Result for r in multi)
        assert multi[0].result == "running new version"
        assert multi[0].changed
        assert not multi.failed


def test_late_events_subscriber_and_latest_progress() -> None:
    gate = threading.Event()
    reported = threading.Event()

    def task(task: Task) -> Generator[Any, None, Result]:
        yield PartialResult(task.host, "first", 0.1)
        reported.set()
        gate.wait(5)
        yield PartialResult(task.host, "second", 0.9)
        return Result(host=task.host)

    nr = make_nornir(ThreadedRunner(), 1)
    handle = nr.submit(task=task)
    reported.wait(5)
    assert handle.progress()["h000"].result == "first"
    events = handle.events()
    gate.set()
    seen = [e.result for e in events if isinstance(e, PartialResult)]
    assert seen == ["second"]
    assert handle.progress()["h000"].progress == pytest.approx(0.9)


def test_subtask_partials_are_tagged_and_run_returns_the_multiresult() -> None:
    def step(task: Task) -> Generator[Any, None, str]:
        yield "copying"
        return "copied"

    returned: list[Any] = []

    def parent(task: Task) -> Result:
        returned.append(task.run(step))
        return Result(host=task.host, result="parent done")

    nr = make_nornir(SerialRunner(), 1)
    events = list(nr.run_stream(task=parent))
    partial = events[0]
    assert isinstance(partial, PartialResult)
    assert (partial.name, partial.result) == ("step", "copying")
    assert returned[0][0].result == "copied"


def test_async_generator_on_a_sync_entry_point_is_rejected() -> None:
    async def agen(task: Task) -> Any:
        await asyncio.sleep(0)
        yield Result(host=task.host)

    nr = make_nornir(ThreadedRunner(), 1)
    with pytest.raises(AsyncTaskOnSyncRunError):
        nr.run(agen)
    with pytest.raises(AsyncTaskOnSyncRunError):
        nr.submit(agen)


def test_wrapper_returning_a_generator_runs_it() -> None:
    def wrapper(task: Task) -> Any:
        return upgrade(task)

    log = EventLog()
    nr = make_nornir(SerialRunner(), 1, [log])
    result = nr.run(task=wrapper)
    assert result["h000"][0].result == "running new version"
    assert [p.result for p in log.partials] == ["uploading", "rebooting"]


def test_plain_values_are_wrapped_and_no_return_gives_none() -> None:
    def task(task: Task) -> Generator[Any, None, None]:
        yield {"stage": 1}

    log = EventLog()
    nr = make_nornir(SerialRunner(), 1, [log])
    result = nr.run(task=task)
    assert log.partials[0].result == {"stage": 1}
    assert log.partials[0].progress is None
    assert result["h000"][0].result is None
    assert not result["h000"].failed


def test_a_yielded_result_ends_the_task() -> None:
    after: list[str] = []

    def task(task: Task) -> Generator[Any, None, None]:
        try:
            yield PartialResult(task.host, "working")
            yield Result(host=task.host, result="final")
            after.append("resumed")
        finally:
            after.append("finally")

    nr = make_nornir(SerialRunner(), 1)
    assert nr.run(task=task)["h000"][0].result == "final"
    assert after == ["finally"]


def test_yield_is_a_checkpoint_and_raises_again() -> None:
    log: list[str] = []
    stream_holder: list[Any] = []

    def task(task: Task) -> Generator[Any, None, Result]:
        try:
            yield "first"
        except TaskCancelledError:
            log.append("caught once")
        try:
            yield "second"
        finally:
            log.append("finally")
        log.append("unreachable")
        return Result(host=task.host)

    nr = make_nornir(SerialRunner(), 1)
    stream = nr.run_stream(task=task)
    stream_holder.append(stream)
    for event in stream:
        if isinstance(event, PartialResult):
            stream.cancel()
    result = stream.result()
    assert log == ["caught once", "finally"]
    assert isinstance(result["h000"][0].exception, TaskCancelledError)


def test_serial_stream_receives_progress_before_the_host_finishes() -> None:
    order: list[str] = []

    def task(task: Task) -> Generator[Any, None, Result]:
        yield "halfway"
        order.append("task resumed")
        return Result(host=task.host)

    nr = make_nornir(SerialRunner(), 1)
    order.extend(type(event).__name__ for event in nr.run_stream(task=task))
    assert order == ["PartialResult", "task resumed", "Result"]


@pytest.mark.parametrize("value", [-0.1, 1.5, float("nan"), True])
def test_progress_must_be_between_zero_and_one(value: Any) -> None:
    nr = make_nornir(SerialRunner(), 1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        PartialResult(nr.inventory.hosts["h000"], progress=value)


def test_generator_task_body_runs_and_is_not_stored_as_a_result() -> None:
    ran: list[str] = []

    def task(task: Task) -> Generator[Any, None, str]:
        ran.append(task.host.name)
        yield "progress"
        return "value"

    nr = make_nornir(ThreadedRunner(), 2)
    result = nr.run(task=task)
    assert sorted(ran) == ["h000", "h001"]
    assert [r[0].result for r in result.values()] == ["value", "value"]
