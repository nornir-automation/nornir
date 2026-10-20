from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING

import pytest

from nornir.core.exceptions import RunnerCapabilityError, TaskCancelledError
from nornir.core.task import AggregatedResult, Result, Task
from nornir.plugins.runners import AsyncioRunner, SerialRunner, ThreadedRunner
from tests.core.run_helpers import EventLog, asteps_task, make_nornir, steps_task

if TYPE_CHECKING:
    from nornir.core.plugins.runners import RunnerPlugin

THREADS: list[str] = []


def fail_second(task: Task) -> Result:
    THREADS.append(threading.current_thread().name)
    if task.host.name == "h001":
        msg = "h001 failed"
        raise ValueError(msg)
    return steps_task(task, steps=20)


def abort_on_first_failure(runner: RunnerPlugin) -> AggregatedResult:
    """Run the calling code under test, which is identical for every runner.

    Returns:
        The results of the run.

    """
    nr = make_nornir(runner, 6)
    stream = nr.run_stream(task=fail_second)
    for event in stream:
        if isinstance(event, Result) and event.failed:
            break
    return stream.result()


def summary(result: AggregatedResult) -> dict[str, str]:
    return {name: type(r[0].exception).__name__ for name, r in result.items()}


def test_same_code_on_serial_and_threaded_runners() -> None:
    THREADS.clear()
    serial = abort_on_first_failure(SerialRunner())
    assert set(THREADS) == {threading.main_thread().name}
    threaded = abort_on_first_failure(ThreadedRunner(num_workers=1))

    assert summary(serial) == summary(threaded)
    assert summary(serial) == {
        "h000": "NoneType",
        "h001": "ValueError",
        "h002": "TaskCancelledError",
        "h003": "TaskCancelledError",
        "h004": "TaskCancelledError",
        "h005": "TaskCancelledError",
    }
    # On SerialRunner the next host only starts when the loop asks for the next event. A
    # threaded worker picks up h002 as soon as h001 ends, so h002 may already be running.
    for result, first_unstarted in ((serial, 2), (threaded, 3)):
        for index in range(first_unstarted, 6):
            error = result[f"h{index:03}"][0].exception
            assert isinstance(error, TaskCancelledError)
            assert error.started is False


def test_submit_on_serial_runner_names_run_stream() -> None:
    nr = make_nornir(SerialRunner(), 2)
    with pytest.raises(RunnerCapabilityError, match="run_stream"):
        nr.submit(task=steps_task)


@pytest.mark.parametrize("runner", [SerialRunner(), ThreadedRunner(num_workers=1)])
def test_an_exception_in_the_loop_body_cancels_the_run(runner: RunnerPlugin) -> None:
    nr = make_nornir(runner, 4)
    stream = nr.run_stream(task=steps_task, steps=20)

    def consume() -> None:
        for _ in stream:
            msg = "consumer failed"
            raise RuntimeError(msg)

    kept_alive: RuntimeError | None = None
    try:
        consume()
    except RuntimeError as error:
        kept_alive = error
    assert kept_alive is not None
    assert kept_alive.__traceback__ is not None
    result = stream.result()
    assert sum(isinstance(r[0].exception, TaskCancelledError) for r in result.values()) >= 3


@pytest.mark.parametrize("runner", [SerialRunner(), ThreadedRunner(num_workers=1)])
def test_leaving_a_with_block_cancels(runner: RunnerPlugin) -> None:
    nr = make_nornir(runner, 4)
    with nr.run_stream(task=steps_task, steps=20) as stream:
        for _ in stream:
            break
    result = stream.result()
    assert sum(isinstance(r[0].exception, TaskCancelledError) for r in result.values()) >= 3


def test_with_block_without_iteration_on_serial_records_every_host() -> None:
    nr = make_nornir(SerialRunner(), 3)
    with nr.run_stream(task=steps_task) as stream:
        pass
    result = stream.result()
    assert all(isinstance(r[0].exception, TaskCancelledError) for r in result.values())
    assert nr.data.failed_hosts == {"h000", "h001", "h002"}


def test_leaving_a_handle_loop_does_not_cancel() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=1), 3)
    handle = nr.submit(task=steps_task, steps=2)
    for _ in handle.results():
        break
    result = handle.result()
    assert all(r[0].result == "done" for r in result.values())


def test_a_stream_is_iterated_once() -> None:
    nr = make_nornir(SerialRunner(), 1)
    stream = nr.run_stream(task=steps_task, steps=1)
    list(stream)
    with pytest.raises(RuntimeError, match="once"):
        iter(stream)


@pytest.mark.parametrize("runner", [SerialRunner(), ThreadedRunner()])
def test_full_stream_then_result(runner: RunnerPlugin) -> None:
    nr = make_nornir(runner, 3)
    stream = nr.run_stream(task=steps_task, steps=1)
    finals = [e for e in stream if isinstance(e, Result)]
    assert len(finals) == 3
    assert all(r[0].result == "done" for r in stream.result().values())


def test_result_without_iterating_runs_the_serial_hosts() -> None:
    nr = make_nornir(SerialRunner(), 2)
    stream = nr.run_stream(task=steps_task, steps=1)
    assert all(r[0].result == "done" for r in stream.result().values())


def test_astream_break_cancels_the_run() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(num_workers=1), 4)
        stream = nr.astream(task=asteps_task, steps=20)
        async for _ in stream:
            break
        result = await stream.result()
        assert sum(isinstance(r[0].exception, TaskCancelledError) for r in result.values()) >= 3

    asyncio.run(scenario())


def test_astream_full_iteration_and_async_with() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 3)
        async with nr.astream(task=asteps_task, steps=1) as stream:
            finals = [e async for e in stream if isinstance(e, Result)]
        assert len(finals) == 3
        assert all(r[0].result == "done" for r in (await stream.result()).values())

    asyncio.run(scenario())


def fail_all(task: Task) -> Result:
    msg = f"{task.host.name} failed"
    raise ValueError(msg)


@pytest.mark.parametrize("runner", [SerialRunner(), ThreadedRunner()])
def test_run_is_finalized_when_a_full_stream_ends(runner: RunnerPlugin) -> None:
    for _ in range(10):
        log = EventLog()
        nr = make_nornir(runner, 3, [log])
        for _ in nr.run_stream(task=fail_all):
            pass
        assert nr.data.failed_hosts == {"h000", "h001", "h002"}
        assert log.hooks()[-1] == "task_completed"


def test_run_is_finalized_when_a_full_astream_ends() -> None:
    async def scenario() -> None:
        for _ in range(10):
            log = EventLog()
            nr = make_nornir(AsyncioRunner(), 3, [log])
            async for _ in nr.astream(task=afail_all):
                pass
            assert nr.data.failed_hosts == {"h000", "h001", "h002"}
            assert log.hooks()[-1] == "task_completed"

    asyncio.run(scenario())


async def afail_all(task: Task) -> Result:
    await asyncio.sleep(0)
    msg = f"{task.host.name} failed"
    raise ValueError(msg)
