from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest

from nornir.core.exceptions import TaskCancelledError
from nornir.core.run import RunContext, RunOptions
from nornir.core.task import Result, Task
from nornir.plugins.runners import SerialRunner
from tests.core.run_helpers import EventLog, make_nornir, make_task

if TYPE_CHECKING:
    from nornir.core import Nornir


def build(task: object, num_hosts: int = 3) -> tuple[Nornir, EventLog, Task, RunContext]:
    log = EventLog()
    nr = make_nornir(SerialRunner(), num_hosts, [log])
    run_task = make_task(nr, task)
    hosts = list(nr.inventory.hosts.values())
    return nr, log, run_task, RunContext(run_task, hosts, RunOptions())


def ok(task: Task) -> Result:
    return Result(host=task.host, result=task.host.name)


def test_a_host_is_recorded_once() -> None:
    nr, log, run_task, run = build(ok)
    host = nr.inventory.hosts["h000"]
    first = run.start_host(run_task.copy(), host)
    assert first[0].result == "h000"
    second = run.start_host(run_task.copy(), host)
    assert second is first
    assert log.hooks("h000") == ["task_instance_started", "task_instance_completed"]


def test_cancel_records_pending_hosts_as_never_started() -> None:
    calls: list[str] = []

    def task(task: Task) -> Result:
        calls.append(task.host.name)
        return Result(host=task.host)

    nr, log, run_task, run = build(task)
    run.cancel()
    assert run.cancelled
    assert run.finished
    for host in nr.inventory.hosts.values():
        assert log.hooks(host.name) == ["task_instance_started", "task_instance_completed"]
        results = run.start_host(run_task.copy(), host)
        error = results[0].exception
        assert isinstance(error, TaskCancelledError)
        assert error.started is False
        assert results[0].failed
    assert calls == []
    assert list(run.aggregated()) == ["h000", "h001", "h002"]


def test_cancel_is_idempotent_and_calls_callbacks_once() -> None:
    _, _, _, run = build(ok)
    calls: list[str] = []
    run.add_cancel_callback(lambda: calls.append("early"))
    run.cancel()
    run.cancel()
    run.add_cancel_callback(lambda: calls.append("late"))
    assert calls == ["early", "late"]


def test_checkpoint_after_cancel_interrupts_and_raises_again() -> None:
    caught: list[TaskCancelledError] = []

    def task(task: Task) -> Result:
        run.cancel()
        for _ in range(2):
            try:
                task.checkpoint()
            except TaskCancelledError as error:
                caught.append(error)
        return Result(host=task.host, result="caught it")

    nr, _, run_task, run = build(task, num_hosts=1)
    results = run.start_host(run_task.copy(), nr.inventory.hosts["h000"])
    assert len(caught) == 2
    assert caught[0] is not caught[1]
    error = results[0].exception
    assert isinstance(error, TaskCancelledError)
    assert error.started is True
    assert results[0].failed


def test_except_exception_around_a_cancelled_subtask_does_not_stop_it() -> None:
    def sub(task: Task) -> Result:
        run.cancel()
        task.checkpoint()
        return Result(host=task.host, result="sub ran")

    def parent(task: Task) -> Result:
        try:
            task.run(sub)
        except Exception:  # the point of the test: must not catch the cancellation
            return Result(host=task.host, result="swallowed")
        return Result(host=task.host, result="finished")

    nr, log, run_task, run = build(parent, num_hosts=1)
    results = run.start_host(run_task.copy(), nr.inventory.hosts["h000"])
    assert isinstance(results[0].exception, TaskCancelledError)
    sub_result = results[1]
    assert sub_result.name == "sub"
    assert sub_result.failed
    assert isinstance(sub_result.exception, TaskCancelledError)
    assert log.hooks("h000") == [
        "task_instance_started",
        "subtask_instance_started",
        "subtask_instance_completed",
        "task_instance_completed",
    ]


def test_starting_a_subtask_after_cancel_is_a_checkpoint() -> None:
    def sub(task: Task) -> Result:
        pytest.fail("the subtask must not start")

    def parent(task: Task) -> Result:
        run.cancel()
        task.run(sub)
        return Result(host=task.host)

    nr, log, run_task, run = build(parent, num_hosts=1)
    results = run.start_host(run_task.copy(), nr.inventory.hosts["h000"])
    assert isinstance(results[0].exception, TaskCancelledError)
    assert "subtask_instance_started" not in log.hooks()


def test_checkpoint_outside_a_run_does_nothing() -> None:
    def task(task: Task) -> Result:
        task.checkpoint()
        return Result(host=task.host, result="fine")

    nr = make_nornir(SerialRunner(), 1)
    assert nr.run(task)["h000"][0].result == "fine"
    standalone = make_task(nr, task)
    assert standalone.start(nr.inventory.hosts["h000"])[0].result == "fine"


def test_finished_and_results_in_completion_order() -> None:
    nr, _, run_task, run = build(ok)
    hosts = list(nr.inventory.hosts.values())
    assert not run.finished
    for host in reversed(hosts):
        run.start_host(run_task.copy(), host)
    assert run.finished
    assert [r.host.name for r in run.completed() if r.host] == ["h002", "h001", "h000"]
    assert list(run.aggregated()) == ["h000", "h001", "h002"]


def test_change_callbacks_fire_on_start_and_record() -> None:
    nr, _, run_task, run = build(ok, num_hosts=1)
    changes: list[str] = []
    run.add_change_callback(lambda: changes.append("change"))
    run.start_host(run_task.copy(), nr.inventory.hosts["h000"])
    assert len(changes) >= 2


def test_cancel_from_another_thread_reaches_a_running_host() -> None:
    entered = threading.Event()

    def task(task: Task) -> Result:
        entered.set()
        while True:
            task.checkpoint()
            threading.Event().wait(0.01)

    nr, _, run_task, run = build(task, num_hosts=1)

    def cancel_when_entered() -> None:
        entered.wait()
        run.cancel()

    canceller = threading.Thread(target=cancel_when_entered)
    canceller.start()
    results = run.start_host(run_task.copy(), nr.inventory.hosts["h000"])
    canceller.join()
    assert isinstance(results[0].exception, TaskCancelledError)
