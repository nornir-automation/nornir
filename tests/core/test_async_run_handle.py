from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING

import pytest

from nornir.core.exceptions import NornirExecutionError, TaskCancelledError
from nornir.core.task import Result, Task
from nornir.plugins.runners import AsyncioRunner
from tests.core.run_helpers import EventLog, ablocked_task, asteps_task, make_nornir

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any


def run(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


async def afail_first(task: Task, steps: int = 50, interval: float = 0.01) -> Result:
    if task.host.name == "h000":
        msg = "h000 failed"
        raise ValueError(msg)
    return await asteps_task(task, steps, interval)


def test_cancel_on_first_failure_accounts_for_every_host() -> None:
    async def scenario() -> None:
        log = EventLog()
        nr = make_nornir(AsyncioRunner(num_workers=5), 20, [log])
        handle = await nr.asubmit(task=afail_first)
        assert log.hooks()[0] == "task_started"
        async for res in handle.results():
            if res.failed:
                handle.cancel()
                break
        result = await handle.result()
        assert list(result) == [f"h{index:03}" for index in range(20)]
        cancelled = [
            r[0].exception
            for r in result.values()
            if isinstance(r[0].exception, TaskCancelledError)
        ]
        assert any(not e.started for e in cancelled)
        assert any(e.started for e in cancelled)
        assert nr.data.failed_hosts == set(nr.inventory.hosts)
        for host in nr.inventory.hosts:
            assert log.hooks(host) == ["task_instance_started", "task_instance_completed"]
        assert log.hooks()[-1] == "task_completed"

    run(scenario())


def test_cancel_interrupts_an_await_without_checkpoint() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 3)
        handle = await nr.asubmit(task=ablocked_task)
        await asyncio.sleep(0.05)
        cancelled_at = time.monotonic()
        handle.cancel()
        result = await handle.result()
        assert time.monotonic() - cancelled_at <= 0.1
        for r in result.values():
            assert isinstance(r[0].exception, TaskCancelledError)
            assert r[0].exception.started

    run(scenario())


def test_cancel_from_another_thread() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 2)
        handle = await nr.asubmit(task=ablocked_task)
        await asyncio.sleep(0.05)
        thread = threading.Thread(target=handle.cancel)
        thread.start()
        result = await asyncio.wait_for(handle.result(), timeout=5)
        thread.join()
        assert all(isinstance(r[0].exception, TaskCancelledError) for r in result.values())

    run(scenario())


def test_cancelling_the_waiter_does_not_cancel_the_run() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 2)
        handle = await nr.asubmit(task=asteps_task, steps=5)
        waiter = asyncio.create_task(handle.result())
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        result = await handle.result()
        assert all(r[0].result == "done" for r in result.values())

    run(scenario())


def test_cancelling_the_arun_coroutine_still_records_nothing() -> None:
    async def scenario() -> None:
        log = EventLog()
        nr = make_nornir(AsyncioRunner(), 3, [log])
        running = asyncio.create_task(nr.arun(task=ablocked_task))
        await asyncio.sleep(0.05)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        assert "task_instance_completed" not in log.hooks()
        assert "task_completed" not in log.hooks()
        assert nr.data.failed_hosts == set()

    run(scenario())


def test_raise_on_error_raises_from_result_only() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 3)
        handle = await nr.asubmit(task=afail_first, raise_on_error=True, steps=1)
        failed = [r async for r in handle.results() if r.failed]
        assert len(failed) == 1
        with pytest.raises(NornirExecutionError):
            await handle.result()

    run(scenario())


def test_results_replay_and_zero_hosts() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 3)
        handle = await nr.asubmit(task=asteps_task, steps=1)
        await handle.result()
        assert handle.done
        first = [r.host.name async for r in handle.results() if r.host]
        second = [r.host.name async for r in handle.results() if r.host]
        assert first == second
        assert len(first) == 3

        empty = await make_nornir(AsyncioRunner(), 0).asubmit(task=asteps_task)
        assert empty.done
        assert dict(await empty.result()) == {}

    run(scenario())


def test_hundred_hosts_finish_within_two_seconds_of_cancel() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(num_workers=100), 100)
        handle = await nr.asubmit(task=asteps_task, steps=60, interval=1.0)
        await asyncio.sleep(0.2)
        cancelled_at = time.monotonic()
        handle.cancel()
        result = await handle.result()
        assert time.monotonic() - cancelled_at <= 2
        assert len(result) == 100

    run(scenario())


def test_handle_is_done_when_results_end() -> None:
    async def scenario() -> None:
        for _ in range(10):
            nr = make_nornir(AsyncioRunner(), 3)
            handle = await nr.asubmit(task=afail_first, steps=1)
            assert len([r async for r in handle.results()]) == 3
            assert handle.done
            assert nr.data.failed_hosts == {"h000"}

    run(scenario())
