"""Type-checked by ``make mypy``: the types the caller of an Operation sees.

The functions are never called; only the type checker reads them.
"""

from __future__ import annotations

from typing import Any

from typing_extensions import assert_type

from nornir.core import Nornir
from nornir.core.inventory import Host
from nornir.core.run import AsyncRunHandle, AsyncRunStream, RunHandle, RunStream
from nornir.core.task import PartialResult, Result
from tests.core.operations_helpers import GetConfig, GetConfigInput, GetConfigOutput


def typed_from_the_class(nr: Nornir) -> None:
    stream = nr.run_operation(GetConfig, GetConfigInput(), connection="napalm")
    assert_type(stream, RunStream[GetConfigOutput])
    for res in stream.results():
        assert_type(res, Result[GetConfigOutput])
        assert_type(res.result.config, str)


def typed_with_a_mapping_and_a_callable(nr: Nornir) -> None:
    assert_type(
        nr.run_operation(GetConfig, {"retrieve": "startup"}, connection="napalm"),
        RunStream[GetConfigOutput],
    )
    assert_type(
        nr.run_operation(GetConfig, lambda host: GetConfigInput(retrieve=host.name)),
        RunStream[GetConfigOutput],
    )


def typed_events(nr: Nornir) -> None:
    for event in nr.run_operation(GetConfig):
        assert_type(event, PartialResult | Result[GetConfigOutput])


def typed_handles(nr: Nornir) -> None:
    handle = nr.submit_operation(GetConfig)
    assert_type(handle, RunHandle[GetConfigOutput])
    assert_type(nr.arun_operation(GetConfig), AsyncRunStream[GetConfigOutput])


async def typed_async_handle(nr: Nornir) -> None:
    handle = await nr.asubmit_operation(GetConfig)
    assert_type(handle, AsyncRunHandle[GetConfigOutput])
    async for res in handle.results():
        assert_type(res.result, GetConfigOutput)


def untyped_by_name(nr: Nornir) -> None:
    assert_type(nr.run_operation("get_config"), RunStream[Any])


# Bare names stay valid under disallow_any_generics, as they were before they became generic.
def bare_result(res: Result) -> Result:
    return res


def bare_run_objects(
    stream: RunStream, handle: RunHandle, astream: AsyncRunStream, ahandle: AsyncRunHandle
) -> tuple[RunStream, RunHandle, AsyncRunStream, AsyncRunHandle]:
    return stream, handle, astream, ahandle


def implementation(task: Any, params: GetConfigInput) -> GetConfigOutput | Result[GetConfigOutput]:
    return GetConfigOutput(config=params.retrieve)


def per_host(host: Host) -> GetConfigInput:
    return GetConfigInput(retrieve=host.name)
