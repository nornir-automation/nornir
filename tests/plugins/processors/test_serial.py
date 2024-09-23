import datetime
import time

from nornir.core import Nornir
from nornir.core.task import Task
from nornir.plugins.runners import SerialRunner


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


class TestSerialRunner:
    def test_blocking_task_single_thread(self, nornir: Nornir) -> None:
        t1 = datetime.datetime.now()
        nornir.with_runner(SerialRunner()).run(blocking_task, wait=0.5)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 3, delta

    def test_failing_task_simple_singlethread(self, nornir: Nornir) -> None:
        result = nornir.with_runner(SerialRunner()).run(failing_task_simple)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, Exception), v
        assert processed

    def test_failing_task_complex_singlethread(self, nornir: Nornir) -> None:
        result = nornir.with_runner(SerialRunner()).run(failing_task_complex)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, CustomException), v
        assert processed
