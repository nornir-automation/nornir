"""Shared helpers for the tests of streaming, cancellation and deadlines (spec 003)."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING, Any

from nornir.core import Nornir
from nornir.core.inventory import Host, Hosts, Inventory
from nornir.core.processor import Processors
from nornir.core.task import Result, Task

if TYPE_CHECKING:
    from collections.abc import Iterable

    from nornir.core.plugins.runners import RunnerPlugin
    from nornir.core.processor import Processor
    from nornir.core.task import AggregatedResult, MultiResult, PartialResult

Event = tuple[str, str, str | None, str]


def make_nornir(
    runner: RunnerPlugin, num_hosts: int, processors: Iterable[Processor] = ()
) -> Nornir:
    """Build a Nornir object with ``num_hosts`` plain hosts named h000, h001, ...

    Returns:
        The Nornir object.

    """
    hosts = Hosts({f"h{index:03}": Host(name=f"h{index:03}") for index in range(num_hosts)})
    return Nornir(
        inventory=Inventory(hosts=hosts),
        runner=runner,
        processors=Processors(list(processors)),
    )


def make_task(nr: Nornir, task: Any, name: str | None = None, **kwargs: Any) -> Task:
    """Build a top-level Task the way Nornir.run does, without running it.

    Returns:
        The task.

    """
    return Task(task, nr, global_dry_run=False, processors=nr.processors, name=name, **kwargs)


class EventLog:
    """Processor recording every hook as (hook, task name, host name, thread name)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events: list[Event] = []
        self.partials: list[PartialResult] = []

    def _add(self, hook: str, task: Task, host: Host | None) -> None:
        with self._lock:
            self.events.append(
                (hook, task.name, host.name if host else None, threading.current_thread().name)
            )

    def hooks(self, host_name: str | None = None) -> list[str]:
        with self._lock:
            return [e[0] for e in self.events if host_name is None or e[2] == host_name]

    def task_started(self, task: Task) -> None:
        self._add("task_started", task, None)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        self._add("task_completed", task, None)

    def task_instance_started(self, task: Task, host: Host) -> None:
        self._add("task_instance_started", task, host)

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self._add("task_instance_completed", task, host)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        self._add("subtask_instance_started", task, host)

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        self._add("subtask_instance_completed", task, host)

    def task_instance_progress(self, task: Task, host: Host, partial: PartialResult) -> None:
        self._add("task_instance_progress", task, host)
        with self._lock:
            self.partials.append(partial)


def steps_task(task: Task, steps: int = 3, interval: float = 0.01) -> Result:
    """Call a checkpoint, then sleep ``interval`` seconds, ``steps`` times.

    Returns:
        A result saying the steps are done.

    """
    for _ in range(steps):
        task.checkpoint()
        time.sleep(interval)
    return Result(host=task.host, result="done")


def fail_now_task(task: Task) -> Result:
    msg = f"{task.host.name} failed"
    raise ValueError(msg)


def blocked_task(task: Task, release: threading.Event) -> Result:
    """Wait for ``release`` without any checkpoint, as a call blocked in I/O would.

    Returns:
        A result saying the task was released.

    """
    release.wait()
    task.checkpoint()
    return Result(host=task.host, result="released")


async def asteps_task(task: Task, steps: int = 3, interval: float = 0.01) -> Result:
    for _ in range(steps):
        task.checkpoint()
        await asyncio.sleep(interval)
    return Result(host=task.host, result="done")


async def ablocked_task(task: Task) -> Result:
    """Wait forever in an awaited call, with no checkpoint.

    Returns:
        Never returns.

    """
    await asyncio.Event().wait()
    return Result(host=task.host, result="unreachable")
