from __future__ import annotations

import math
import threading
import time
from typing import TYPE_CHECKING, Any

import pytest

from nornir.core.configuration import Config, RunnerConfig
from nornir.core.exceptions import TaskTimeoutError
from nornir.core.run import RunOptions
from nornir.core.task import Result, Task
from nornir.init_nornir import load_runner
from nornir.plugins.runners import AsyncioRunner, SerialRunner, ThreadedRunner
from tests.core.run_helpers import EventLog, blocked_task, make_nornir, steps_task

if TYPE_CHECKING:
    from nornir.core.task import AggregatedResult


def timeouts(result: AggregatedResult) -> dict[str, TaskTimeoutError]:
    return {
        name: r[0].exception
        for name, r in result.items()
        if isinstance(r[0].exception, TaskTimeoutError)
    }


def blocked_first(task: Task, release: threading.Event) -> Result:
    if task.host.name == "h000":
        return blocked_task(task, release)
    return steps_task(task, steps=1, interval=0.01)


def test_run_deadline_returns_on_time_with_a_blocked_host(release: threading.Event) -> None:
    nr = make_nornir(ThreadedRunner(num_workers=2, timeout=2), 6)

    def task(task: Task, release: threading.Event) -> Result:
        if task.host.name in {"h000", "h001"}:
            return blocked_task(task, release)
        return steps_task(task, steps=1)

    started = time.monotonic()
    result = nr.run(task=task, release=release)
    assert time.monotonic() - started <= 3
    expired = timeouts(result)
    assert set(expired) == set(nr.inventory.hosts)
    assert expired["h000"].started
    assert expired["h000"].scope == "run"
    assert not expired["h002"].started


def test_per_run_options_override_the_runner() -> None:
    nr = make_nornir(ThreadedRunner(per_host_timeout=600), 1)
    run = nr.submit(task=steps_task, steps=50, run_options=RunOptions(per_host_timeout=0.2))
    error = timeouts(run.result(timeout=5))["h000"]
    assert (error.scope, error.timeout) == ("host", 0.2)

    nr = make_nornir(ThreadedRunner(per_host_timeout=0.2), 1)
    run = nr.submit(task=steps_task, steps=50, run_options=RunOptions(timeout=600))
    assert timeouts(run.result(timeout=5))["h000"].scope == "host"


def test_runner_per_host_timeout_applies_to_plain_run() -> None:
    nr = make_nornir(ThreadedRunner(per_host_timeout=0.2), 3)
    result = nr.run(task=steps_task, steps=50)
    assert set(timeouts(result)) == {"h000", "h001", "h002"}
    assert nr.data.failed_hosts == {"h000", "h001", "h002"}


def test_task_parameter_named_timeout_still_reaches_the_task() -> None:
    received: list[Any] = []

    def task(task: Task, timeout: int) -> Result:
        received.append(timeout)
        return Result(host=task.host)

    nr = make_nornir(ThreadedRunner(), 1)
    nr.run(task, timeout=30)
    assert received == [30]


def test_serial_deadline_at_the_next_checkpoint() -> None:
    log = EventLog()
    nr = make_nornir(SerialRunner(per_host_timeout=0.2), 2, [log])
    result = nr.run(task=steps_task, steps=50)
    assert set(timeouts(result)) == {"h000", "h001"}
    assert log.hooks("h001") == ["task_instance_started", "task_instance_completed"]


def test_serial_blocked_host_delays_the_caller(release: threading.Event) -> None:
    nr = make_nornir(SerialRunner(per_host_timeout=0.1), 2)
    threading.Timer(0.5, release.set).start()
    started = time.monotonic()
    result = nr.run(task=blocked_first, release=release)
    assert time.monotonic() - started >= 0.5
    assert set(timeouts(result)) == {"h000"}
    assert result["h001"][0].result == "done"


def test_per_host_clock_starts_when_the_host_starts() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=1, per_host_timeout=0.5), 3)
    result = nr.run(task=steps_task, steps=3, interval=0.1)
    assert timeouts(result) == {}


@pytest.mark.parametrize("value", [0, -1, math.inf, math.nan, True, "1"])
def test_invalid_timeouts_are_rejected(value: Any) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        RunOptions(per_host_timeout=value)
    with pytest.raises(ValueError, match="positive finite"):
        RunOptions(timeout=value)
    for runner in (SerialRunner, ThreadedRunner, AsyncioRunner):
        with pytest.raises(ValueError, match="positive finite"):
            runner(timeout=value)


def test_configuration_file_options_reach_the_runner() -> None:
    config = Config(
        runner=RunnerConfig(
            plugin="threaded", options={"per_host_timeout": 1, "timeout": 5, "num_workers": 3}
        )
    )
    runner = load_runner(config)
    assert isinstance(runner, ThreadedRunner)
    assert runner.run_options == RunOptions(per_host_timeout=1, timeout=5)
    assert runner.num_workers == 3


def test_late_worker_fires_no_further_event(release: threading.Event) -> None:
    log = EventLog()
    nr = make_nornir(ThreadedRunner(per_host_timeout=0.2), 1, [log])
    result = nr.run(task=blocked_task, release=release)
    assert set(timeouts(result)) == {"h000"}
    release.set()
    time.sleep(0.2)
    assert log.hooks("h000") == ["task_instance_started", "task_instance_completed"]
