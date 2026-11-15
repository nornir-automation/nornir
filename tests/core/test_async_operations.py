from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest

from nornir.core.exceptions import (
    RunnerCapabilityError,
    RunnerNotAsyncError,
    SyncTaskOnAsyncRunError,
)
from nornir.core.operations import OperationRegistry
from nornir.core.task import PartialResult, Result
from nornir.plugins.runners import AsyncioRunner, SerialRunner
from tests.core.operations_helpers import (
    GetConfig,
    GetConfigInput,
    GetConfigOutput,
    aeos_get_config,
    aios_get_config,
    junos_get_config,
    make_nornir,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Coroutine

    from nornir.core.task import Task

pytestmark = pytest.mark.usefixtures("operation_registry")


def run(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


def register_async() -> None:
    for platform, task in (("ios", aios_get_config), ("eos", aeos_get_config)):
        OperationRegistry.register(
            operation="get_config", platform=platform, connection="napalm", task=task
        )


def test_arun_operation_yields_typed_results() -> None:
    register_async()

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), {"r1": "ios", "r2": "eos"})
        stream = nr.arun_operation(
            GetConfig, GetConfigInput(retrieve="startup"), connection="napalm"
        )
        configs = {}
        async for res in stream.results():
            assert res.host is not None
            configs[res.host.name] = res.result.config
        assert configs == {"r1": "ios startup r1", "r2": "eos startup r2"}
        assert not (await stream.result()).failed

    run(scenario())


def test_asubmit_operation_returns_a_handle() -> None:
    register_async()

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), {"r1": "ios", "r2": "eos"})
        handle = await nr.asubmit_operation(GetConfig, connection="napalm")
        configs = {res.host.name: res.result.config async for res in handle.results() if res.host}
        assert configs == {"r1": "ios running r1", "r2": "eos running r2"}
        assert not (await handle.result()).failed

    run(scenario())


def test_async_stream_yields_partial_results() -> None:
    async def progress(task: Task, params: GetConfigInput) -> AsyncGenerator[Any, None]:
        yield PartialResult(task.host, "fetching")
        await asyncio.sleep(0)
        yield Result(task.host, result=GetConfigOutput(config="ios"))

    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=progress
    )

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), {"r1": "ios"})
        events = [e async for e in nr.arun_operation(GetConfig, connection="napalm")]
        assert [type(e).__name__ for e in events] == ["PartialResult", "Result"]

    run(scenario())


def test_leaving_async_results_early_cancels_the_run() -> None:
    async def slow(task: Task, params: GetConfigInput) -> GetConfigOutput:
        if task.host.name != "r1":
            for _ in range(100):
                task.checkpoint()
                await asyncio.sleep(0.01)
        return GetConfigOutput(config=task.host.name)

    for platform in ("ios", "eos"):
        OperationRegistry.register(
            operation="get_config", platform=platform, connection="napalm", task=slow
        )

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), {"r1": "ios", "r2": "eos"})
        stream = nr.arun_operation(GetConfig, connection="napalm")
        results = stream.results()
        async for _ in results:
            break
        await results.aclose()
        result = await stream.result()
        assert result["r2"].failed

    run(scenario())


def test_synchronous_task_on_an_asynchronous_run_fails_the_host() -> None:
    register_async()
    OperationRegistry.register(
        operation="get_config", platform="junos", connection="napalm", task=junos_get_config
    )

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner())
        result = await nr.arun_operation(GetConfig, connection="napalm").result()
        assert result["r1"][0].exception is None
        assert result["r2"][0].exception is None
        error = result["r3"][0].exception
        assert isinstance(error, SyncTaskOnAsyncRunError)
        assert str(error).startswith(
            "Task 'junos_get_config' (selected for operation 'get_config' on host 'r3') is "
            "synchronous and cannot run asynchronously."
        )

    run(scenario())


def test_arun_operation_on_a_synchronous_runner_raises() -> None:
    register_async()

    async def scenario() -> None:
        nr = make_nornir(SerialRunner())
        with pytest.raises(RunnerNotAsyncError):
            nr.arun_operation(GetConfig, connection="napalm")
        with pytest.raises(RunnerNotAsyncError):
            await nr.asubmit_operation(GetConfig, connection="napalm")

    run(scenario())


def test_capability_error_names_the_operation_method() -> None:
    error = RunnerCapabilityError("MyRunner", "arun_operation")
    assert "Implement AsyncStreamingRunner" in str(error)
