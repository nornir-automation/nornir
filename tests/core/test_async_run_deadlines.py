from __future__ import annotations

import asyncio
import time

from nornir.core.exceptions import TaskTimeoutError
from nornir.core.run import RunOptions
from nornir.core.task import Result, Task
from nornir.plugins.runners import AsyncioRunner
from tests.core.run_helpers import ablocked_task, asteps_task, make_nornir


def test_per_host_deadline_interrupts_an_await_without_checkpoint() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(per_host_timeout=0.5), 3)
        started = time.monotonic()
        result = await nr.arun(task=ablocked_task)
        assert time.monotonic() - started <= 0.6
        for r in result.values():
            error = r[0].exception
            assert isinstance(error, TaskTimeoutError)
            assert (error.scope, error.started) == ("host", True)

    asyncio.run(scenario())


def test_run_deadline_records_semaphore_waiters_as_never_started() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(num_workers=1), 3)
        handle = await nr.asubmit(task=ablocked_task, run_options=RunOptions(timeout=0.3))
        result = await asyncio.wait_for(handle.result(), timeout=2)
        errors = [r[0].exception for r in result.values()]
        assert all(isinstance(e, TaskTimeoutError) and e.scope == "run" for e in errors)
        assert [e.started for e in errors if isinstance(e, TaskTimeoutError)] == [
            True,
            False,
            False,
        ]

    asyncio.run(scenario())


def test_swallowed_cancellation_is_interrupted_at_the_next_checkpoint() -> None:
    reached: list[str] = []

    async def stubborn(task: Task) -> Result:
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            reached.append("swallowed")
        task.checkpoint()
        reached.append("unreachable")
        return Result(host=task.host)

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(per_host_timeout=0.2), 1)
        result = await asyncio.wait_for(nr.arun(task=stubborn), timeout=2)
        assert isinstance(result["h000"][0].exception, TaskTimeoutError)

    asyncio.run(scenario())
    assert reached == ["swallowed"]


def test_hosts_within_their_deadline_keep_their_results() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(per_host_timeout=2), 3)
        result = await nr.arun(task=asteps_task, steps=2)
        assert all(r[0].result == "done" for r in result.values())

    asyncio.run(scenario())
