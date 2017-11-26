import datetime
import time
from multiprocessing import cpu_count

from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import commands

import pytest

NUM_WORKERS = cpu_count()


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

    def test_blocking_task_single_thread(self, brigade):
        brigade.num_workers = 1
        t1 = datetime.datetime.now()
        brigade.run(blocking_task, wait=0.5)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_blocking_task_multithreading(self, brigade):
        brigade.num_workers = NUM_WORKERS
        t1 = datetime.datetime.now()
        brigade.run(blocking_task, wait=2)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_failing_task_simple_singlethread(self, brigade):
        brigade.num_workers = 1
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_simple)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, Exception), v

    def test_failing_task_simple_multithread(self, brigade):
        brigade.num_workers = NUM_WORKERS
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_simple)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, Exception), v

    def test_failing_task_complex_singlethread(self, brigade):
        brigade.num_workers = 1
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_complex)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, CommandError), v

    def test_failing_task_complex_multithread(self, brigade):
        brigade.num_workers = NUM_WORKERS
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_complex)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, CommandError), v

    def test_change_data_in_thread(self, brigade):
        brigade.num_workers = NUM_WORKERS
        brigade.run(change_data)
        brigade.run(verify_data_change)
