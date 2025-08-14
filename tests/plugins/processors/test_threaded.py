import datetime
import time

import pytest

from nornir.core import Nornir
from nornir.core.exceptions import NornirExecutionError
from nornir.core.task import Task
from nornir.plugins.runners import ThreadedRunner

NUM_WORKERS = 20


class CustomException(Exception):
    pass


def a_task_for_testing(task: Task, command: str) -> None:
    if command == "failme":
        raise CustomException()


def blocking_task(task: Task, wait: float) -> None:
    time.sleep(wait)


def failing_task_simple(task: Task) -> None:
    raise Exception(task.host.name)


def failing_task_complex(task: Task) -> None:
    a_task_for_testing(task, command="failme")


def change_data(task: Task) -> None:
    task.host["my_changed_var"] = task.host.name


def verify_data_change(task: Task) -> None:
    assert task.host["my_changed_var"] == task.host.name


class Test:
    def test_blocking_task_multithreading(self, nornir: Nornir) -> None:
        t1 = datetime.datetime.now()
        nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(blocking_task, wait=2)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_failing_task_simple_multithread(self, nornir: Nornir) -> None:
        result = nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            failing_task_simple,
        )
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, Exception), v
        assert processed

    def test_failing_task_complex_multithread(self, nornir: Nornir) -> None:
        result = nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            failing_task_complex,
        )
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, CustomException), v
        assert processed

    def test_failing_task_complex_multithread_raise_on_error(self, nornir: Nornir) -> None:
        with pytest.raises(NornirExecutionError) as e:
            nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
                failing_task_complex, raise_on_error=True
            )
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v.exception, CustomException), v

    def test_change_data_in_thread(self, nornir: Nornir) -> None:
        nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            change_data,
        )
        nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            verify_data_change,
        )
