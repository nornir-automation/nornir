import datetime
import time

from nornir.plugins.runners import SerialRunner


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


class TestSerialRunner(object):
    def test_blocking_task_single_thread(self, nornir):
        t1 = datetime.datetime.now()
        nornir.with_runner(SerialRunner()).run(blocking_task, wait=0.5)
        t2 = datetime.datetime.now()
        delta = t2 - t1
        assert delta.seconds == 2, delta

    def test_failing_task_simple_singlethread(self, nornir):
        result = nornir.with_runner(SerialRunner()).run(failing_task_simple)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, Exception), v
        assert processed

    def test_failing_task_complex_singlethread(self, nornir):
        result = nornir.with_runner(SerialRunner()).run(failing_task_complex)
        processed = False
        for k, v in result.items():
            processed = True
            assert isinstance(k, str), k
            assert isinstance(v.exception, CustomException), v
        assert processed
