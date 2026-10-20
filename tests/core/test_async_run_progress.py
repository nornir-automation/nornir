from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest

from nornir.core.exceptions import SyncTaskOnAsyncRunError, TaskCancelledError
from nornir.core.task import PartialResult, Result, Task
from nornir.plugins.runners import AsyncioRunner
from tests.core.run_helpers import EventLog, make_nornir

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def aupgrade(task: Task) -> AsyncGenerator[Any, None]:
    yield PartialResult(host=task.host, result="uploading", progress=0.2)
    await asyncio.sleep(0)
    yield PartialResult(host=task.host, result="rebooting", progress=0.7)
    yield Result(host=task.host, result="running new version", changed=True)


def test_astream_delivers_partials_then_the_final_result() -> None:
    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 2)
        events = [e async for e in nr.astream(task=aupgrade)]
        for host in ("h000", "h001"):
            mine = [e for e in events if e.host and e.host.name == host]
            assert [type(e).__name__ for e in mine] == [
                "PartialResult",
                "PartialResult",
                "Result",
            ]
            assert mine[-1].result == "running new version"

    asyncio.run(scenario())


def test_handle_events_and_arun_with_a_progress_processor() -> None:
    async def scenario() -> None:
        log = EventLog()
        nr = make_nornir(AsyncioRunner(), 1, [log])
        handle = await nr.asubmit(task=aupgrade)
        partials = [e.result async for e in handle.events() if isinstance(e, PartialResult)]
        assert partials == ["uploading", "rebooting"]
        result = await nr.arun(task=aupgrade)
        assert result["h000"][0].changed
        assert all(type(r) is Result for r in result["h000"])
        assert len(log.partials) == 4

    asyncio.run(scenario())


def test_def_generator_on_async_entry_points_is_rejected() -> None:
    def gen(task: Task) -> Any:
        yield Result(host=task.host)

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 1)
        with pytest.raises(SyncTaskOnAsyncRunError):
            await nr.arun(gen)
        with pytest.raises(SyncTaskOnAsyncRunError):
            await nr.asubmit(gen)

    asyncio.run(scenario())


def test_cancel_interrupts_an_async_generator_at_its_await() -> None:
    cleaned: list[str] = []

    async def waits(task: Task) -> AsyncGenerator[Any, None]:
        yield "started"
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.append(task.host.name)
        yield Result(host=task.host)

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), 2)
        handle = await nr.asubmit(task=waits)
        await asyncio.sleep(0.05)
        handle.cancel()
        result = await asyncio.wait_for(handle.result(), timeout=2)
        assert all(isinstance(r[0].exception, TaskCancelledError) for r in result.values())

    asyncio.run(scenario())
    assert sorted(cleaned) == ["h000", "h001"]
