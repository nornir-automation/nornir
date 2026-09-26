import asyncio
import functools
from collections.abc import Callable, Coroutine
from typing import Any, cast

import pytest

from nornir.core import Nornir
from nornir.core.exceptions import (
    AsyncTaskOnSyncRunError,
    NornirSubTaskError,
    SyncTaskOnAsyncRunError,
)
from nornir.core.inventory import Host
from nornir.core.processor import Processors
from nornir.core.task import AggregatedResult, MultiResult, Result, Task


class RecordingProcessor:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def task_started(self, task: Task) -> None:
        self.events.append(("task_started", task.name))

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.events.append(("task_completed", task.name))

    def task_instance_started(self, task: Task, host: Host) -> None:
        self.events.append(("task_instance_started", task.name))

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.events.append(("task_instance_completed", task.name))

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        self.events.append(("subtask_instance_started", task.name))

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.events.append(("subtask_instance_completed", task.name))


def make_task(
    nornir: Nornir,
    processor: RecordingProcessor,
    task: Callable[..., Any],
    name: str | None = None,
) -> Task:
    return Task(
        task=task,
        nornir=nornir,
        global_dry_run=False,
        processors=Processors([processor]),
        name=name,
    )


def first_host(nornir: Nornir) -> Host:
    return next(iter(nornir.inventory.hosts.values()))


def sync_child(task: Task) -> Result:
    return Result(host=task.host, result="sync")


async def async_grandchild(task: Task) -> Result:
    await asyncio.sleep(0)
    return Result(host=task.host, result="grandchild")


async def async_child(task: Task) -> Result:
    await task.arun(async_grandchild)
    task.run(sync_child)
    return Result(host=task.host, result="child")


async def nested_parent(task: Task) -> Result:
    await task.arun(async_child)
    return Result(host=task.host, result="parent")


def test_astart_preserves_nested_results_and_events(nornir: Nornir) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        result = await make_task(nornir, processor, nested_parent).astart(first_host(nornir))

        assert result[0].name == "nested_parent"
        assert result[0].result == "parent"
        child = result[1]
        assert isinstance(child, MultiResult)
        assert [(item.name, item.result) for item in child] == [
            ("async_child", "child"),
            ("async_grandchild", "grandchild"),
            ("sync_child", "sync"),
        ]
        assert processor.events == [
            ("task_instance_started", "nested_parent"),
            ("subtask_instance_started", "async_child"),
            ("subtask_instance_started", "async_grandchild"),
            ("subtask_instance_completed", "async_grandchild"),
            ("subtask_instance_started", "sync_child"),
            ("subtask_instance_completed", "sync_child"),
            ("subtask_instance_completed", "async_child"),
            ("task_instance_completed", "nested_parent"),
        ]

    asyncio.run(exercise())


class ChildError(Exception):
    pass


async def failing_child(task: Task) -> None:
    await asyncio.sleep(0)
    raise ChildError("child failed")


async def uncaught_failure_parent(task: Task) -> None:
    await task.arun(failing_child)


def test_failed_async_child_becomes_failed_parent_result(nornir: Nornir) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        result = await make_task(nornir, processor, uncaught_failure_parent).astart(
            first_host(nornir)
        )

        assert result.failed
        assert isinstance(result[0].exception, NornirSubTaskError)
        assert isinstance(result[1].exception, ChildError)
        assert result[0].result == "Subtask: failing_child (failed)\n"
        assert "failing_child" in str(result[0].exception)
        assert processor.events == [
            ("task_instance_started", "uncaught_failure_parent"),
            ("subtask_instance_started", "failing_child"),
            ("subtask_instance_completed", "failing_child"),
            ("task_instance_completed", "uncaught_failure_parent"),
        ]

    asyncio.run(exercise())


def sync_mismatch_child(task: Task) -> None:
    raise AssertionError("synchronous child must not execute")


async def async_mismatch_child(task: Task) -> None:
    await asyncio.sleep(0)
    raise AssertionError("asynchronous child must not execute")


async def catch_async_entry_mismatch(task: Task) -> Result:
    before = list(task.results)
    with pytest.raises(SyncTaskOnAsyncRunError) as error:
        await task.arun(cast("Callable[..., Coroutine[Any, Any, Any]]", sync_mismatch_child))
    assert error.value.task_name == "sync_mismatch_child"
    assert task.results == before
    return Result(host=task.host, result="caught")


async def catch_sync_entry_mismatch(task: Task) -> Result:
    await asyncio.sleep(0)
    before = list(task.results)
    with pytest.raises(AsyncTaskOnSyncRunError) as error:
        task.run(async_mismatch_child)
    assert error.value.task_name == "async_mismatch_child"
    assert task.results == before
    return Result(host=task.host, result="caught")


@pytest.mark.parametrize("parent", [catch_async_entry_mismatch, catch_sync_entry_mismatch])
def test_child_mismatch_has_no_child_result_or_events(
    nornir: Nornir,
    parent: Callable[[Task], Coroutine[Any, Any, Result]],
) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        result = await make_task(nornir, processor, parent).astart(first_host(nornir))

        assert not result.failed
        assert len(result) == 1
        assert result[0].result == "caught"
        assert processor.events == [
            ("task_instance_started", parent.__name__),
            ("task_instance_completed", parent.__name__),
        ]

    asyncio.run(exercise())


async def uncaught_mismatch_parent(task: Task) -> None:
    await task.arun(cast("Callable[..., Coroutine[Any, Any, Any]]", sync_mismatch_child))


def test_uncaught_child_mismatch_uses_normal_parent_failure_conversion(nornir: Nornir) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        result = await make_task(nornir, processor, uncaught_mismatch_parent).astart(
            first_host(nornir)
        )

        assert len(result) == 1
        assert isinstance(result[0].exception, SyncTaskOnAsyncRunError)
        assert "uncaught_mismatch_parent" in result[0].result
        assert processor.events == [
            ("task_instance_started", "uncaught_mismatch_parent"),
            ("task_instance_completed", "uncaught_mismatch_parent"),
        ]

    asyncio.run(exercise())


async def named_partial_child(task: Task, value: str) -> Result:
    await asyncio.sleep(0)
    return Result(host=task.host, result=value)


class NamedAsyncCallable:
    async def __call__(self, task: Task) -> Result:
        return Result(host=task.host, result="callable")


async def callable_forms_parent(task: Task) -> None:
    partial = functools.partial(named_partial_child, value="partial")
    await task.arun(partial, name="explicit partial")
    await task.arun(NamedAsyncCallable(), name="explicit callable")


def test_async_callable_forms_preserve_explicit_names(nornir: Nornir) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        result = await make_task(nornir, processor, callable_forms_parent).astart(
            first_host(nornir)
        )

        assert [(item.name, item.result) for item in result] == [
            ("callable_forms_parent", None),
            ("explicit partial", "partial"),
            ("explicit callable", "callable"),
        ]

    asyncio.run(exercise())


async def traceback_source_task(task: Task) -> None:
    await asyncio.sleep(0)
    raise ChildError("traceback marker")


def test_astart_traceback_points_to_user_async_function(nornir: Nornir) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        result = await make_task(nornir, processor, traceback_source_task).astart(
            first_host(nornir)
        )

        traceback_text = result[0].result
        assert "test_async_tasks.py" in traceback_text
        assert "in traceback_source_task" in traceback_text
        assert 'raise ChildError("traceback marker")' in traceback_text

    asyncio.run(exercise())


async def cancelled_task(task: Task) -> None:
    await asyncio.sleep(0)
    raise asyncio.CancelledError


def test_astart_does_not_convert_base_exception_to_result(nornir: Nornir) -> None:
    async def exercise() -> None:
        processor = RecordingProcessor()
        task = make_task(nornir, processor, cancelled_task)

        with pytest.raises(asyncio.CancelledError):
            await task.astart(first_host(nornir))

        assert task.results == []
        assert processor.events == [("task_instance_started", "cancelled_task")]

    asyncio.run(exercise())
