import logging

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result


class CustomException(Exception):
    pass


def a_task_for_testing(task, fail_on=None):
    fail_on = fail_on or []
    if task.host.name in fail_on:
        raise CustomException()
    return Result(host=task.host, stdout=task.host.name)


def a_failed_task_for_testing(task):
    return Result(host=task.host, stdout=task.host.name, failed=True)


def a_failed_task_for_testing_overrides_severity(task):
    return Result(
        host=task.host,
        stdout=task.host.name,
        failed=True,
        severity_level=logging.CRITICAL,
    )


def a_task_to_test_dry_run(task, expected_dry_run_value, dry_run=None):
    assert task.is_dry_run(dry_run) is expected_dry_run_value


def sub_task_for_testing(task, fail_on=None):
    task.run(
        a_task_for_testing,
        fail_on=fail_on,
    )


def sub_task_for_testing_overrides_severity(task, fail_on=None):
    task.run(
        a_task_for_testing,
        fail_on=fail_on,
        severity_level=logging.DEBUG,
    )


def fail_command_subtask_no_capture(task, fail_on=None):
    task.run(a_task_for_testing, fail_on=fail_on)
    return "I shouldn't be here"


def fail_command_subtask_capture(task, fail_on=None):
    try:
        task.run(a_task_for_testing, fail_on=fail_on)
    except Exception:
        return "I captured this succcessfully"


class Test(object):
    def test_task(self, nornir):
        result = nornir.run(a_task_for_testing)
        assert result
        for h, r in result.items():
            assert r.stdout.strip() == h

    def test_sub_task(self, nornir):
        result = nornir.run(sub_task_for_testing)
        assert result
        for h, r in result.items():
            assert r[0].name == "sub_task_for_testing"
            assert r[1].name == "a_task_for_testing"
            assert h == r[1].stdout.strip()

    def test_skip_failed_host(self, nornir):
        result = nornir.run(sub_task_for_testing, fail_on=["dev3.group_2"])
        assert result.failed
        assert "dev3.group_2" in result

        for h, r in result.items():
            if h == "dev3.group_2":
                assert r.failed
            else:
                assert not r.failed
                assert h == r[1].stdout.strip()

        result = nornir.run(a_task_for_testing)
        assert not result.failed
        assert "dev3.group_2" not in result

    def test_run_on(self, nornir):
        result = nornir.run(a_task_for_testing, fail_on=["dev3.group_2"])
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" in result

        result = nornir.run(
            a_task_for_testing, fail_on=["dev3.group_2"], on_failed=True
        )
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" in result

        result = nornir.run(
            a_task_for_testing, fail_on=["dev3.group_2"], on_failed=True, on_good=False
        )
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" not in result

        result = nornir.run(
            a_task_for_testing, fail_on=["dev3.group_2"], on_failed=False, on_good=True
        )
        assert not result.failed
        assert "dev3.group_2" not in result
        assert "dev1.group_1" in result

    def test_severity(self, nornir):
        r = nornir.run(a_task_for_testing)
        for host, result in r.items():
            assert result[0].severity_level == logging.INFO

        r = nornir.run(a_task_for_testing, severity_level=logging.WARN)
        for host, result in r.items():
            assert result[0].severity_level == logging.WARN

        r = nornir.run(sub_task_for_testing, severity_level=logging.WARN)
        for host, result in r.items():
            for sr in result:
                assert sr.severity_level == logging.WARN

        r = nornir.run(
            sub_task_for_testing_overrides_severity,
            fail_on=["dev3.group_2"],
            severity_level=logging.WARN,
        )
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result[0].severity_level == logging.ERROR
            else:
                assert result[0].severity_level == logging.WARN
                assert result[1].severity_level == logging.DEBUG

        r = nornir.run(a_failed_task_for_testing)
        for host, result in r.items():
            assert result[0].severity_level == logging.ERROR
        # Reset all failed host for next test
        nornir.data.reset_failed_hosts()

        r = nornir.run(a_failed_task_for_testing, severity_level=logging.WARN)
        for host, result in r.items():
            assert result[0].severity_level == logging.ERROR
        # Reset all failed host for next test
        nornir.data.reset_failed_hosts()

        r = nornir.run(a_failed_task_for_testing_overrides_severity)
        for host, result in r.items():
            assert result[0].severity_level == logging.CRITICAL
        # Reset all failed host for next test
        nornir.data.reset_failed_hosts()

    def test_dry_run(self, nornir):
        host = nornir.filter(name="dev3.group_2")
        r = host.run(a_task_to_test_dry_run, expected_dry_run_value=True)
        assert not r["dev3.group_2"].failed

        r = host.run(
            a_task_to_test_dry_run, dry_run=False, expected_dry_run_value=False
        )
        assert not r["dev3.group_2"].failed

        nornir.data.dry_run = False
        r = host.run(a_task_to_test_dry_run, expected_dry_run_value=False)
        assert not r["dev3.group_2"].failed

        nornir.data.dry_run = True
        r = host.run(a_task_to_test_dry_run, expected_dry_run_value=False)
        assert r["dev3.group_2"].failed

    def test_subtask_exception_no_capture(self, nornir):
        host = nornir.filter(name="dev1.group_1")
        r = host.run(task=fail_command_subtask_no_capture, fail_on=["dev1.group_1"])
        assert r.failed
        assert r["dev1.group_1"][0].exception.__class__ is NornirSubTaskError
        assert r["dev1.group_1"][1].exception.__class__ is CustomException

    def test_subtask_exception_capture(self, nornir):
        host = nornir.filter(name="dev1.group_1")
        r = host.run(task=fail_command_subtask_capture, fail_on=["dev1.group_1"])
        assert r.failed
        assert not r["dev1.group_1"][0].exception
        assert r["dev1.group_1"][0].result == "I captured this succcessfully"
        assert r["dev1.group_1"][1].exception.__class__ is CustomException
