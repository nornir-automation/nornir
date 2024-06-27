import datetime
import time

import pytest

from nornir.core.exceptions import NornirExecutionError
from nornir.plugins.runners import ThreadedRunner

NUM_WORKERS = 20


class CustomException(Exception):
    pass


def a_task_for_testing(task, command):
    if command == "failme":
        raise CustomException()


def blocking_task(task, wait):
    time.sleep(wait)


def failing_task_simple(task):
    raise Exception(task.host.name)


def failing_task_complex(task):
    a_task_for_testing(task, command="failme")


def change_data(task):
    task.host["my_changed_var"] = task.host.name


def verify_data_change(task):
    assert task.host["my_changed_var"] == task.host.name


class Test(object):
    def test_blocking_task_multithreading(self, nornir):
        t1 = datetime.datetime.now()
        nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(blocking_task, wait=2)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_failing_task_simple_multithread(self, nornir):
        result = nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            failing_task_simple,
        )
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, Exception), v
        assert processed

    def test_failing_task_complex_multithread(self, nornir):
        result = nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            failing_task_complex,
        )
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, CustomException), v
        assert processed

    def test_failing_task_complex_multithread_raise_on_error(self, nornir):
        with pytest.raises(NornirExecutionError) as e:
            nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
                failing_task_complex, raise_on_error=True
            )
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v.exception, CustomException), v

    def test_change_data_in_thread(self, nornir):
        nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            change_data,
        )
        nornir.with_runner(ThreadedRunner(num_workers=NUM_WORKERS)).run(
            verify_data_change,
        )
