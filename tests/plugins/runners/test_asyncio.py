from __future__ import annotations

import asyncio
import gc
import threading
import time
from collections.abc import Awaitable, Callable, Coroutine
from itertools import pairwise
from typing import Any, TypeVar, cast

import pytest

from nornir.core import Nornir
from nornir.core.exceptions import RunnerNotSyncError
from nornir.core.inventory import Host, Hosts, Inventory
from nornir.core.processor import Processors
from nornir.core.task import AggregatedResult, MultiResult, Result, Task
from nornir.plugins.runners import AsyncioRunner

AsyncTask = Callable[[Task], Awaitable[Result]]
T = TypeVar("T")


class RecordingProcessor:
    def __init__(self) -> None:
        self.events: list[tuple[str, str | None]] = []

    def task_started(self, task: Task) -> None:
        self.events.append(("task_started", None))

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self.events.append(("task_completed", None))

    def task_instance_started(self, task: Task, host: Host) -> None:
        self.events.append(("task_instance_started", host.name))

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.events.append(("task_instance_completed", host.name))

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        self.events.append(("subtask_instance_started", host.name))

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self.events.append(("subtask_instance_completed", host.name))


def make_hosts(count: int) -> list[Host]:
    return [Host(name=f"host-{index:04}") for index in range(count)]


def make_task(task: AsyncTask, hosts: list[Host]) -> Task:
    inventory = Inventory(hosts=Hosts({host.name: host for host in hosts}))
    nornir = Nornir(inventory=inventory, runner=AsyncioRunner())
    return Task(task, nornir, global_dry_run=False, processors=Processors())


def make_nornir(
    hosts: list[Host], runner: AsyncioRunner, processor: RecordingProcessor
) -> Nornir:
    inventory = Inventory(hosts=Hosts({host.name: host for host in hosts}))
    return Nornir(
        inventory=inventory,
        runner=runner,
        processors=Processors([processor]),
    )


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


async def host_name(task: Task) -> Result:
    await asyncio.gather()
    return Result(host=task.host, result=task.host.name)


def test_results_follow_input_host_order() -> None:
    async def scenario() -> None:
        hosts = make_hosts(5)
        release = {host.name: asyncio.Event() for host in hosts}
        completed = {host.name: asyncio.Event() for host in hosts}
        completion_order: list[str] = []
        all_waiting = asyncio.Event()
        waiting = 0

        async def complete_out_of_order(task: Task) -> Result:
            nonlocal waiting
            waiting += 1
            if waiting == len(hosts):
                all_waiting.set()
            await release[task.host.name].wait()
            completion_order.append(task.host.name)
            completed[task.host.name].set()
            return Result(host=task.host, result=task.host.name)

        running = asyncio.create_task(
            AsyncioRunner().arun(make_task(complete_out_of_order, hosts), hosts)
        )
        await asyncio.wait_for(all_waiting.wait(), timeout=1)
        for host in reversed(hosts):
            release[host.name].set()
            await asyncio.wait_for(completed[host.name].wait(), timeout=1)

        result = await running
        assert completion_order == [host.name for host in reversed(hosts)]
        assert list(result) == [host.name for host in hosts]
        assert [item[0].result for item in result.values()] == [host.name for host in hosts]

    run(scenario())


def test_host_failure_does_not_cancel_siblings() -> None:
    async def scenario() -> None:
        hosts = make_hosts(3)
        completed: set[str] = set()

        async def fail_one(task: Task) -> Result:
            await asyncio.gather()
            if task.host.name == hosts[1].name:
                raise RuntimeError("independent failure")
            completed.add(task.host.name)
            return Result(host=task.host, result="ok")

        result = await AsyncioRunner().arun(make_task(fail_one, hosts), hosts)
        assert result[hosts[1].name].failed
        assert isinstance(result[hosts[1].name].exception, RuntimeError)
        assert completed == {hosts[0].name, hosts[2].name}

    run(scenario())


@pytest.mark.parametrize(("num_workers", "host_count"), [(1, 4), (3, 8), (20, 25), (10, 3)])
def test_concurrency_is_bounded(num_workers: int, host_count: int) -> None:
    async def scenario() -> None:
        hosts = make_hosts(host_count)
        expected_active = min(num_workers, host_count)
        all_active = asyncio.Event()
        release = asyncio.Event()
        active = 0
        maximum_active = 0

        async def blocked(task: Task) -> Result:
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            if active == expected_active:
                all_active.set()
            await release.wait()
            active -= 1
            return Result(host=task.host, result=True)

        running = asyncio.create_task(
            AsyncioRunner(num_workers).arun(make_task(blocked, hosts), hosts)
        )
        await asyncio.wait_for(all_active.wait(), timeout=1)
        assert maximum_active == expected_active
        release.set()
        await running
        assert active == 0

    run(scenario())


def test_default_worker_count_is_twenty() -> None:
    assert AsyncioRunner().num_workers == 20


def test_worker_count_above_inventory_size() -> None:
    hosts = make_hosts(2)
    result = run(AsyncioRunner(100).arun(make_task(host_name, hosts), hosts))
    assert list(result) == [host.name for host in hosts]


def test_empty_host_input() -> None:
    result = run(AsyncioRunner().arun(make_task(host_name, []), []))
    assert result == {}
    assert result.name == "host_name"


@pytest.mark.parametrize("num_workers", [True, False, 1.5, "2", None])
def test_non_integer_worker_count_is_rejected(num_workers: object) -> None:
    with pytest.raises(TypeError, match=r"num_workers.*integer"):
        AsyncioRunner(cast("int", num_workers))


@pytest.mark.parametrize("num_workers", [0, -1, -100])
def test_non_positive_worker_count_is_rejected(num_workers: int) -> None:
    with pytest.raises(ValueError, match=r"num_workers.*positive"):
        AsyncioRunner(num_workers)


def test_sync_run_is_unconditionally_rejected() -> None:
    runner = AsyncioRunner()
    with pytest.raises(RunnerNotSyncError) as exc_info:
        runner.run(cast("Task", object()), [])
    assert exc_info.value.runner_name == "AsyncioRunner"
    assert "await nr.arun" in str(exc_info.value)


def test_cancellation_cancels_and_drains_all_owned_tasks() -> None:
    async def scenario() -> None:
        hosts = make_hosts(4)
        started = asyncio.Event()
        drained: set[str] = set()
        active = 0
        cleanup_checkpoint = asyncio.Event()
        cleanup_checkpoint.set()

        async def blocked(task: Task) -> Result:
            nonlocal active
            active += 1
            if active == len(hosts):
                started.set()
            try:
                await asyncio.Event().wait()
            finally:
                await cleanup_checkpoint.wait()
                drained.add(task.host.name)
                active -= 1
            raise AssertionError("blocked task unexpectedly resumed")

        running = asyncio.create_task(AsyncioRunner(4).arun(make_task(blocked, hosts), hosts))
        await asyncio.wait_for(started.wait(), timeout=1)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        assert active == 0
        assert drained == {host.name for host in hosts}

    run(scenario())


def test_repeated_cancellation_does_not_interrupt_child_cleanup() -> None:
    async def scenario() -> None:
        hosts = make_hosts(2)
        started = asyncio.Event()
        cleaning = asyncio.Event()
        release_cleanup = asyncio.Event()
        drained: set[str] = set()
        active = 0
        cleaning_count = 0

        async def blocked(task: Task) -> Result:
            nonlocal active, cleaning_count
            active += 1
            if active == len(hosts):
                started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaning_count += 1
                if cleaning_count == len(hosts):
                    cleaning.set()
                await release_cleanup.wait()
                drained.add(task.host.name)
                active -= 1
            raise AssertionError("blocked task unexpectedly resumed")

        running = asyncio.create_task(AsyncioRunner(2).arun(make_task(blocked, hosts), hosts))
        await asyncio.wait_for(started.wait(), timeout=1)
        running.cancel()
        await asyncio.wait_for(cleaning.wait(), timeout=1)
        running.cancel()
        second_cancel_processed = asyncio.Event()
        asyncio.get_running_loop().call_soon(second_cancel_processed.set)
        await second_cancel_processed.wait()
        assert not running.done()
        release_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await running
        assert active == 0
        assert drained == {host.name for host in hosts}

    run(scenario())


def test_cancellation_drains_twenty_active_hosts_and_semaphore_waiters() -> None:
    async def scenario() -> None:
        hosts = make_hosts(25)
        processor = RecordingProcessor()
        nr = make_nornir(hosts, AsyncioRunner(), processor)
        nr.data.failed_hosts.add("preserved-failure")
        all_active = asyncio.Event()
        all_cleaning = asyncio.Event()
        release_cleanup = asyncio.Event()
        active_hosts: set[str] = set()
        cleaned_hosts: set[str] = set()
        cleaning = 0

        async def blocked(task: Task) -> Result:
            nonlocal cleaning
            active_hosts.add(task.host.name)
            if len(active_hosts) == 20:
                all_active.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaning += 1
                if cleaning == 20:
                    all_cleaning.set()
                await release_cleanup.wait()
                cleaned_hosts.add(task.host.name)
            raise AssertionError("blocked task unexpectedly resumed")

        existing_tasks = asyncio.all_tasks()
        running = asyncio.create_task(nr.arun(task=blocked))
        await asyncio.wait_for(all_active.wait(), timeout=1)
        assert sum(event == "task_instance_started" for event, _ in processor.events) == 20

        running.cancel()
        await asyncio.wait_for(all_cleaning.wait(), timeout=1)
        running.cancel()
        running.cancel()
        cancellation_processed = asyncio.Event()
        asyncio.get_running_loop().call_soon(cancellation_processed.set)
        await cancellation_processed.wait()

        assert not running.done()
        assert nr.data.failed_hosts == {"preserved-failure"}
        assert processor.events[0] == ("task_started", None)
        assert ("task_completed", None) not in processor.events
        assert all(event != "task_instance_completed" for event, _ in processor.events)

        release_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await running

        assert cleaned_hosts == active_hosts
        assert len(cleaned_hosts) == 20
        assert ("task_completed", None) not in processor.events
        assert asyncio.all_tasks() <= existing_tasks

    run(scenario())


def test_prompt_child_does_not_end_drain_before_awaited_finally_child() -> None:
    async def scenario() -> None:
        hosts = make_hosts(3)
        processor = RecordingProcessor()
        nr = make_nornir(hosts, AsyncioRunner(2), processor)
        both_active = asyncio.Event()
        prompt_cleaned = asyncio.Event()
        awaited_cleaning = asyncio.Event()
        release_awaited_cleanup = asyncio.Event()
        active = 0

        async def blocked(task: Task) -> Result:
            nonlocal active
            active += 1
            if active == 2:
                both_active.set()
            try:
                await asyncio.Event().wait()
            finally:
                if task.host is hosts[0]:
                    prompt_cleaned.set()
                else:
                    awaited_cleaning.set()
                    await release_awaited_cleanup.wait()
            raise AssertionError("blocked task unexpectedly resumed")

        existing_tasks = asyncio.all_tasks()
        running = asyncio.create_task(nr.arun(task=blocked))
        await asyncio.wait_for(both_active.wait(), timeout=1)
        running.cancel()
        await asyncio.wait_for(prompt_cleaned.wait(), timeout=1)
        await asyncio.wait_for(awaited_cleaning.wait(), timeout=1)

        assert not running.done()
        assert nr.data.failed_hosts == set()
        assert ("task_completed", None) not in processor.events

        release_awaited_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await running

        assert sum(event == "task_instance_started" for event, _ in processor.events) == 2
        assert all(event != "task_instance_completed" for event, _ in processor.events)
        assert asyncio.all_tasks() <= existing_tasks

    run(scenario())


def test_cancellation_retrieves_aggregate_exception_and_leaves_no_owned_tasks() -> None:
    async def scenario() -> None:
        hosts = make_hosts(2)
        processor = RecordingProcessor()
        nr = make_nornir(hosts, AsyncioRunner(2), processor)
        all_active = asyncio.Event()
        active = 0
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        exception_contexts: list[dict[str, Any]] = []

        def record_exception(
            _event_loop: asyncio.AbstractEventLoop, context: dict[str, Any]
        ) -> None:
            exception_contexts.append(context)

        async def blocked(task: Task) -> Result:
            nonlocal active
            active += 1
            if active == len(hosts):
                all_active.set()
            await asyncio.Event().wait()
            raise AssertionError("blocked task unexpectedly resumed")

        existing_tasks = asyncio.all_tasks()
        loop.set_exception_handler(record_exception)
        try:
            running = asyncio.create_task(nr.arun(task=blocked))
            await asyncio.wait_for(all_active.wait(), timeout=1)
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
            del running
            await asyncio.sleep(0)
            gc.collect()
            await asyncio.sleep(0)
        finally:
            loop.set_exception_handler(previous_handler)

        assert exception_contexts == []
        assert nr.data.failed_hosts == set()
        assert processor.events[0] == ("task_started", None)
        assert ("task_completed", None) not in processor.events
        assert asyncio.all_tasks() <= existing_tasks

    run(scenario())


def test_async_io_keeps_the_event_loop_responsive() -> None:
    async def scenario() -> None:
        hosts = make_hosts(100)
        ready = asyncio.Event()
        stop = asyncio.Event()
        heartbeats: list[float] = []

        async def io_task(task: Task) -> Result:
            await asyncio.sleep(0.1)
            return Result(host=task.host, result=True)

        async def heartbeat() -> None:
            heartbeats.append(time.monotonic())
            ready.set()
            while not stop.is_set():
                await asyncio.sleep(0.01)
                heartbeats.append(time.monotonic())

        pulse = asyncio.create_task(heartbeat())
        await ready.wait()
        await AsyncioRunner(100).arun(make_task(io_task, hosts), hosts)
        heartbeats.append(time.monotonic())
        stop.set()
        await pulse
        gaps = [later - earlier for earlier, later in pairwise(heartbeats)]
        assert gaps
        assert max(gaps) <= 0.05

    run(scenario())


def test_one_thousand_hosts_complete_under_two_seconds_without_threads() -> None:
    async def scenario() -> None:
        hosts = make_hosts(1_000)

        async def io_task(task: Task) -> Result:
            await asyncio.sleep(0.1)
            return Result(host=task.host, result=True)

        task = make_task(io_task, hosts)
        threads_before = threading.active_count()
        started = time.monotonic()
        result = await AsyncioRunner(1_000).arun(task, hosts)
        elapsed = time.monotonic() - started
        assert elapsed < 2
        assert len(result) == 1_000
        assert threading.active_count() == threads_before

    run(scenario())
