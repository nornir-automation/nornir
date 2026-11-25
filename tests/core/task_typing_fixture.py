"""Type-checked by ``make mypy``: the types the caller of a plain task sees.

The functions are never called; only the type checker reads them.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from typing_extensions import assert_type

from nornir.core.run import AsyncRunHandle, AsyncRunStream, RunHandle, RunStream
from nornir.core.task import AggregatedResult, MultiResult, PartialResult, Result
from tests.core.operations_helpers import GetConfig, GetConfigOutput

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Callable, Generator, Iterator

    from nornir.core import Nornir
    from nornir.core.task import Task


@dataclass
class Facts:
    hostname: str
    version: str


def get_facts(task: Task) -> Result[Facts]:
    return Result(task.host, result=Facts(hostname=task.host.name, version="17.9"))


def get_version(task: Task) -> tuple[int, int]:
    return (17, 9)


def configure(task: Task) -> None:
    task.run(get_version)


def bare_result(task: Task) -> Result:
    return Result(task.host)


def progress(task: Task) -> Generator[PartialResult, None, Result[Facts]]:
    yield PartialResult(task.host, "fetching")
    return get_facts(task)  # noqa: B901 - a generator task may return its final result


def iter_progress(task: Task) -> Iterator[str]:
    yield "fetching"


def maybe_facts(task: Task) -> Optional[Result[Facts]]:  # noqa: UP045 - the spelling under test
    return None if task.host.name == "skip" else get_facts(task)


def maybe_bare(task: Task) -> Result | None:
    return None if task.host.name == "skip" else Result(task.host)


async def aget_facts(task: Task) -> Result[Facts]:
    await asyncio.sleep(0)
    return get_facts(task)


async def aget_version(task: Task) -> str:
    await asyncio.sleep(0)
    return "17.9"


async def aprogress(task: Task) -> AsyncGenerator[Any, None]:
    await asyncio.sleep(0)
    yield get_facts(task)


async def aiter_progress(task: Task) -> AsyncIterator[str]:
    await asyncio.sleep(0)
    yield "fetching"


async def amaybe_facts(task: Task) -> Result[Facts] | None:
    await asyncio.sleep(0)
    return None if task.host.name == "skip" else get_facts(task)


def run_is_typed_from_the_task(nr: Nornir) -> None:
    result = nr.run(task=get_facts)
    assert_type(result, AggregatedResult[Facts])
    assert_type(result["r1"], MultiResult[Facts])
    assert_type(result["r1"].result, Facts)
    assert_type(result["r1"].result.version, str)
    # The other entries are the results of subtasks, which return other types.
    assert_type(result["r1"][0], Result[Any])
    # A failed task holds the error text, so failed hosts are not typed.
    assert_type(result.failed_hosts, dict[str, MultiResult[Any]])


def run_wraps_a_plain_return_value(nr: Nornir) -> None:
    assert_type(nr.run(get_version), AggregatedResult[tuple[int, int]])
    assert_type(nr.run(configure), AggregatedResult[None])
    assert_type(
        nr.run(get_version, name="version", on_failed=True), AggregatedResult[tuple[int, int]]
    )


def untyped_tasks_stay_any(nr: Nornir, untyped: Callable[..., Any]) -> None:
    assert_type(nr.run(untyped), AggregatedResult[Any])
    assert_type(nr.run(bare_result), AggregatedResult[Any])
    # A generator task may end by returning a value or by yielding a Result.
    assert_type(nr.run(progress), AggregatedResult[Any])
    # Nornir drives a generator annotated as an Iterator too; .result is not the iterator.
    assert_type(nr.run(iter_progress), AggregatedResult[Any])
    assert_type(nr.stream(iter_progress), RunStream[Any])
    assert_type(nr.submit(iter_progress), RunHandle[Any])


def an_optional_result_gives_the_value_inside_it_or_none(nr: Nornir) -> None:
    # A task returning None records a Result whose result is None.
    assert_type(nr.run(maybe_facts), AggregatedResult[Facts | None])
    assert_type(nr.run(maybe_bare), AggregatedResult[Any | None])
    assert_type(nr.stream(maybe_facts), RunStream[Facts | None])
    assert_type(nr.submit(maybe_facts), RunHandle[Facts | None])


def streams_and_handles_are_typed(nr: Nornir) -> None:
    stream = nr.stream(get_facts)
    assert_type(stream, RunStream[Facts])
    for res in stream.results():
        assert_type(res.result, Facts)
    assert_type(stream.result(), AggregatedResult[Facts])
    handle = nr.submit(get_version)
    assert_type(handle, RunHandle[tuple[int, int]])
    assert_type(handle.result(), AggregatedResult[tuple[int, int]])
    assert_type(nr.stream(progress), RunStream[Any])


async def async_entry_points_are_typed(nr: Nornir) -> None:
    assert_type(await nr.arun(aget_facts), AggregatedResult[Facts])
    assert_type(await nr.arun(aget_version), AggregatedResult[str])
    assert_type(await nr.arun(aprogress), AggregatedResult[Any])
    assert_type(await nr.arun(aiter_progress), AggregatedResult[Any])
    assert_type(nr.astream(aiter_progress), AsyncRunStream[Any])
    assert_type(await nr.asubmit(aiter_progress), AsyncRunHandle[Any])
    assert_type(await nr.arun(amaybe_facts), AggregatedResult[Facts | None])
    assert_type(nr.astream(amaybe_facts), AsyncRunStream[Facts | None])
    assert_type(await nr.asubmit(amaybe_facts), AsyncRunHandle[Facts | None])
    stream = nr.astream(aget_version)
    assert_type(stream, AsyncRunStream[str])
    assert_type(await stream.result(), AggregatedResult[str])
    handle = await nr.asubmit(aget_facts)
    assert_type(handle, AsyncRunHandle[Facts])
    assert_type(await handle.result(), AggregatedResult[Facts])


def subtasks_are_typed(task: Task) -> None:
    assert_type(task.run(get_version), MultiResult[tuple[int, int]])
    assert_type(task.run(get_version).result, tuple[int, int])
    assert_type(task.run(get_facts).result, Facts)
    assert_type(task.run(progress), MultiResult[Any])
    assert_type(task.run(iter_progress), MultiResult[Any])
    assert_type(task.run(maybe_facts).result, Facts | None)


async def async_subtasks_are_typed(task: Task) -> None:
    assert_type((await task.arun(aget_version)).result, str)
    assert_type((await task.arun(aget_facts)).result, Facts)
    assert_type(await task.arun(aprogress), MultiResult[Any])
    assert_type(await task.arun(aiter_progress), MultiResult[Any])
    assert_type((await task.arun(amaybe_facts)).result, Facts | None)


def operation_results_are_typed(nr: Nornir) -> None:
    assert_type(nr.run_operation(GetConfig).result(), AggregatedResult[GetConfigOutput])


# Bare names stay valid under disallow_any_generics, as they were before they became generic.
def bare_names(result: AggregatedResult, multi: MultiResult) -> MultiResult:
    return result.get("r1", multi)
