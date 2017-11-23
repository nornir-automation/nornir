import datetime
import os
import time

from brigade.core import Brigade
from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import commands

import pytest


dir_path = os.path.dirname(os.path.realpath(__file__))

brigade = Brigade(
    inventory=SimpleInventory("{}/inventory_data/hosts.yaml".format(dir_path),
                              "{}/inventory_data/groups.yaml".format(dir_path)),
    dry_run=True,
    num_workers=20,
)


def blocking_task(task, wait):
    time.sleep(wait)


def failing_task_simple(task):
    raise Exception(task.host.name)


def failing_task_complex(task):
    commands.command(task, command="ls /folderdoesntexist")


class Test(object):

    def test_blocking_task_single_thread(self):
        brigade.num_workers = 1
        t1 = datetime.datetime.now()
        brigade.run(blocking_task, wait=0.5)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_blocking_task_multithreading(self):
        brigade.num_workers = 20
        t1 = datetime.datetime.now()
        brigade.run(blocking_task, wait=2)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_failing_task_simple_singlethread(self):
        brigade.num_workers = 1
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_simple)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, Exception), v

    def test_failing_task_simple_multithread(self):
        brigade.num_workers = 20
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_simple)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, Exception), v

    def test_failing_task_complex_singlethread(self):
        brigade.num_workers = 1
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_complex)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, CommandError), v

    def test_failing_task_complex_multithread(self):
        brigade.num_workers = 20
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(failing_task_complex)
        for k, v in e.value.result.items():
            assert isinstance(k, str), k
            assert isinstance(v, CommandError), v
