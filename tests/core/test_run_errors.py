from __future__ import annotations

import pickle  # noqa: S403 - only round-trips objects the test itself creates

import pytest

from nornir.core.exceptions import (
    RunnerCapabilityError,
    SyncAsyncMismatchError,
    TaskCancelledError,
    TaskInterruptedError,
    TaskTimeoutError,
)


def test_interruptions_are_base_exceptions_but_not_exceptions() -> None:
    assert issubclass(TaskInterruptedError, BaseException)
    assert not issubclass(TaskInterruptedError, Exception)
    assert issubclass(TaskCancelledError, TaskInterruptedError)
    assert issubclass(TaskTimeoutError, TaskInterruptedError)
    assert not issubclass(TaskCancelledError, TaskTimeoutError)


def test_except_exception_does_not_catch_an_interruption() -> None:
    def interrupted() -> None:
        raise TaskCancelledError("rtr-1", "upgrade")

    def swallow() -> None:
        try:
            interrupted()
        except Exception:  # the point of the test: this handler must not run
            pytest.fail("except Exception caught a cancellation")

    with pytest.raises(TaskCancelledError):
        swallow()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            TaskCancelledError("rtr-1", "upgrade"),
            "Task 'upgrade' on host 'rtr-1' was cancelled.",
        ),
        (
            TaskCancelledError("rtr-1", "upgrade", started=False),
            "Task 'upgrade' on host 'rtr-1' was cancelled before it started.",
        ),
        (
            TaskTimeoutError("rtr-1", "upgrade", 600, "host"),
            "Task 'upgrade' on host 'rtr-1' exceeded its per-host timeout of 600 seconds.",
        ),
        (
            TaskTimeoutError("rtr-1", "upgrade", 3600, "run"),
            "Task 'upgrade' on host 'rtr-1' exceeded the run timeout of 3600 seconds.",
        ),
        (
            TaskTimeoutError("rtr-1", "upgrade", 3600, "run", started=False),
            "Task 'upgrade' on host 'rtr-1' did not start before the run timeout of 3600 seconds.",
        ),
        (
            TaskTimeoutError("rtr-1", "upgrade", 0.5, "host"),
            "Task 'upgrade' on host 'rtr-1' exceeded its per-host timeout of 0.5 seconds.",
        ),
    ],
)
def test_interruption_messages(error: TaskInterruptedError, message: str) -> None:
    assert str(error) == message


def test_interruption_fields() -> None:
    cancelled = TaskCancelledError("rtr-1", "upgrade", started=False)
    assert (cancelled.host_name, cancelled.task_name, cancelled.started) == (
        "rtr-1",
        "upgrade",
        False,
    )
    timed_out = TaskTimeoutError("rtr-2", "copy", 30, "run")
    assert (timed_out.timeout, timed_out.scope, timed_out.started) == (30, "run", True)


@pytest.mark.parametrize(
    "error",
    [
        TaskCancelledError("rtr-1", "upgrade"),
        TaskCancelledError("rtr-1", "upgrade", started=False),
        TaskTimeoutError("rtr-1", "upgrade", 600, "host"),
        TaskTimeoutError("rtr-1", "upgrade", 60, "run", started=False),
        RunnerCapabilityError("MyRunner", "run_stream"),
        RunnerCapabilityError("SerialRunner", "submit", background=True),
    ],
)
def test_errors_pickle_with_their_fields(error: BaseException) -> None:
    copy = pickle.loads(pickle.dumps(error))  # noqa: S301 - round-trip of our own object
    assert type(copy) is type(error)
    assert str(copy) == str(error)
    assert vars(copy) == vars(error)


def test_runner_capability_error() -> None:
    assert issubclass(RunnerCapabilityError, Exception)
    assert not issubclass(RunnerCapabilityError, SyncAsyncMismatchError)

    missing = RunnerCapabilityError("MyRunner", "run_stream")
    assert (missing.runner_name, missing.capability) == ("MyRunner", "run_stream")
    assert str(missing) == (
        "MyRunner does not support 'run_stream'. Implement StreamingRunner, or use run()."
    )
    assert str(RunnerCapabilityError("MyRunner", "astream")) == (
        "MyRunner does not support 'astream'. Implement AsyncStreamingRunner, or use arun()."
    )

    serial = RunnerCapabilityError("SerialRunner", "submit", background=True)
    assert str(serial) == (
        "SerialRunner does not support background runs ('submit') because it runs every "
        "task on the caller's thread. Use 'run_stream' to consume the run live, or use "
        "ThreadedRunner."
    )
