from __future__ import annotations

import threading
import time

import pytest

from nornir.core.exceptions import NornirExecutionError, TaskCancelledError
from nornir.core.task import Result, Task
from nornir.plugins.runners import ThreadedRunner
from tests.core.run_helpers import EventLog, blocked_task, make_nornir, steps_task


def fail_first(task: Task, steps: int = 50, interval: float = 0.01) -> Result:
    if task.host.name == "h000":
        msg = "h000 failed"
        raise ValueError(msg)
    return steps_task(task, steps, interval)


def test_cancel_on_first_failure_accounts_for_every_host() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=5), 20)
    run = nr.submit(task=fail_first)
    seen = []
    for res in run.results():
        seen.append(res.host.name if res.host else None)
        if res.failed:
            run.cancel()
            break
    result = run.result()

    assert seen[0] == "h000"
    assert list(result) == [f"h{index:03}" for index in range(20)]
    assert result["h000"][0].exception.__class__ is ValueError
    cancelled = [r[0] for r in result.values() if isinstance(r[0].exception, TaskCancelledError)]
    assert cancelled
    never_started = [
        r
        for r in cancelled
        if isinstance(r.exception, TaskCancelledError) and not r.exception.started
    ]
    assert never_started, "queued hosts must be recorded as never started"
    assert all(r.failed for r in cancelled)


def test_failed_hosts_are_updated_without_reading_the_result() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=2), 6)
    run = nr.submit(task=fail_first)
    run.cancel()
    deadline = time.monotonic() + 5
    while not run.done and time.monotonic() < deadline:
        time.sleep(0.01)
    assert run.done
    assert nr.data.failed_hosts == set(nr.inventory.hosts)


def test_processor_events_in_order_including_never_started_hosts() -> None:
    log = EventLog()
    nr = make_nornir(ThreadedRunner(num_workers=1), 4, [log])
    started = threading.Event()

    def task(task: Task) -> Result:
        started.set()
        return steps_task(task, steps=100)

    run = nr.submit(task=task)
    assert log.hooks()[0] == "task_started"
    started.wait(5)
    run.cancel()
    run.result()

    hooks = log.hooks()
    assert hooks[0] == "task_started"
    assert hooks[-1] == "task_completed"
    assert hooks.count("task_completed") == 1
    for host in nr.inventory.hosts:
        assert log.hooks(host) == ["task_instance_started", "task_instance_completed"]


def test_raise_on_error_raises_from_result_only() -> None:
    log = EventLog()
    nr = make_nornir(ThreadedRunner(), 3, [log])
    run = nr.submit(task=fail_first, raise_on_error=True, steps=1)
    failed = [r for r in run.results() if r.failed]
    assert len(failed) == 1
    with pytest.raises(NornirExecutionError):
        run.result()
    with pytest.raises(NornirExecutionError):
        run.result()
    assert "task_completed" not in log.hooks()
    assert nr.data.failed_hosts == set()


def test_two_threads_read_the_same_results_and_cancel_twice() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=4), 8)
    run = nr.submit(task=steps_task, steps=2)
    orders: list[list[str]] = []

    def read() -> None:
        orders.append([r.host.name for r in run.results() if r.host])

    readers = [threading.Thread(target=read) for _ in range(2)]
    for reader in readers:
        reader.start()
    for reader in readers:
        reader.join(10)
    run.cancel()
    run.cancel()
    assert len(orders) == 2
    assert orders[0] == orders[1]
    assert sorted(orders[0]) == sorted(nr.inventory.hosts)


def test_results_replays_hosts_that_already_finished() -> None:
    nr = make_nornir(ThreadedRunner(), 5)
    run = nr.submit(task=steps_task, steps=1)
    run.result()
    first = [r.host.name for r in run.results() if r.host]
    second = [r.host.name for r in run.results() if r.host]
    assert first == second
    assert len(first) == 5


def test_hosts_are_selected_when_submit_is_called() -> None:
    nr = make_nornir(ThreadedRunner(), 3)
    nr.data.failed_hosts.add("h001")
    run = nr.submit(task=steps_task, steps=1)
    nr.data.failed_hosts.clear()
    assert list(run.result()) == ["h000", "h002"]


def test_cancel_before_any_host_starts() -> None:
    gate = threading.Event()
    log = EventLog()
    nr = make_nornir(ThreadedRunner(num_workers=1), 4, [log])

    def first_waits(task: Task) -> Result:
        gate.wait(5)
        task.checkpoint()
        return Result(host=task.host)

    run = nr.submit(task=first_waits)
    run.cancel()
    gate.set()
    result = run.result()
    errors = [r[0].exception for r in result.values()]
    assert all(isinstance(e, TaskCancelledError) for e in errors)
    assert sum(1 for e in errors if isinstance(e, TaskCancelledError) and not e.started) >= 3


def test_blocked_host_is_recorded_only_when_it_reaches_a_checkpoint(
    release: threading.Event,
) -> None:
    nr = make_nornir(ThreadedRunner(), 1)
    run = nr.submit(task=blocked_task, release=release)
    time.sleep(0.05)
    run.cancel()
    with pytest.raises(TimeoutError):
        run.result(timeout=0.5)
    release.set()
    result = run.result(timeout=5)
    assert isinstance(result["h000"][0].exception, TaskCancelledError)


def test_zero_selected_hosts_gives_a_finished_handle() -> None:
    log = EventLog()
    nr = make_nornir(ThreadedRunner(), 0, [log])
    run = nr.submit(task=steps_task)
    assert run.done
    assert dict(run.result()) == {}
    assert list(run.results()) == []
    assert list(run.events()) == []
    assert log.hooks() == ["task_started", "task_completed"]


def test_result_timeout_and_unique_ids() -> None:
    nr = make_nornir(ThreadedRunner(), 2)
    run = nr.submit(task=steps_task, steps=30)
    other = nr.submit(task=steps_task, steps=1)
    with pytest.raises(TimeoutError):
        run.result(timeout=0.01)
    run.cancel()
    run.result()
    other.result()
    assert run.id != other.id


def test_hundred_hosts_finish_within_two_seconds_of_cancel() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=100), 100)
    run = nr.submit(task=steps_task, steps=60, interval=1.0)
    time.sleep(0.2)
    cancelled_at = time.monotonic()
    run.cancel()
    result = run.result(timeout=10)
    assert time.monotonic() - cancelled_at <= 2
    assert len(result) == 100
    assert all(isinstance(r[0].exception, TaskCancelledError) for r in result.values())


def test_events_yield_final_results() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=1), 3)
    gate = threading.Event()

    def task(task: Task) -> Result:
        gate.wait(5)
        return Result(host=task.host, result=task.host.name)

    run = nr.submit(task=task)
    events = run.events()
    gate.set()
    names = [e.host.name for e in events if isinstance(e, Result) and e.host]
    assert sorted(names) == ["h000", "h001", "h002"]
    assert run.progress() == {}


def test_handle_is_done_when_results_end() -> None:
    for _ in range(10):
        nr = make_nornir(ThreadedRunner(), 3)
        handle = nr.submit(task=fail_first, steps=1)
        assert len(list(handle.results())) == 3
        assert handle.done
        assert nr.data.failed_hosts == {"h000"}
