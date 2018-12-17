import datetime
import time

from nornir.core.exceptions import NornirExecutionError, CommandError
from nornir.plugins.tasks import commands

import pytest


NUM_WORKERS = 20


def blocking_task(task, wait):
    time.sleep(wait)


def failing_task_simple(task):
    raise Exception(task.host.name)


def failing_task_complex(task):
    commands.command(task, command="ls /folderdoesntexist")


def change_data(task):
    task.host["my_changed_var"] = task.host.name


def verify_data_change(task):
    assert task.host["my_changed_var"] == task.host.name


class Test(object):
    def test_blocking_task_single_thread(self, nornir):
        t1 = datetime.datetime.now()
        nornir.run(blocking_task, wait=0.5, num_workers=1)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_blocking_task_multithreading(self, nornir):
        t1 = datetime.datetime.now()
        nornir.run(blocking_task, wait=2, num_workers=NUM_WORKERS)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_failing_task_simple_singlethread(self, nornir):
        result = nornir.run(failing_task_simple, num_workers=1)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, Exception), v
        assert processed

    def test_failing_task_simple_multithread(self, nornir):
        result = nornir.run(failing_task_simple, num_workers=NUM_WORKERS)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, Exception), v
        assert processed

    def test_failing_task_complex_singlethread(self, nornir):
        result = nornir.run(failing_task_complex, num_workers=1)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, CommandError), v
        assert processed

    def test_failing_task_complex_multithread(self, nornir):
        result = nornir.run(failing_task_complex, num_workers=NUM_WORKERS)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, CommandError), v
        assert processed

    def test_failing_task_complex_multithread_raise_on_error(self, nornir):
        with pytest.raises(NornirExecutionError) as e:
            nornir.run(
                failing_task_complex, num_workers=NUM_WORKERS, raise_on_error=True
            )
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v.exception, CommandError), v

    def test_change_data_in_thread(self, nornir):
        nornir.run(change_data, num_workers=NUM_WORKERS)
        nornir.run(verify_data_change, num_workers=NUM_WORKERS)
