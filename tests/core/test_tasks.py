import logging

from nornir.core.exceptions import CommandError, NornirSubTaskError

from nornir.plugins.tasks import commands


def a_task_to_test_dry_run(task, expected_dry_run_value, dry_run=None):
    assert task.is_dry_run(dry_run) is expected_dry_run_value


def task_fails_for_some(task):
    if task.host.name == "dev3.group_2":
        # let's hardcode a failure
        task.run(commands.command, command="sasdasdasd")
    else:
        task.run(
            commands.command,
            command="echo {}".format(task.host),
            severity_level=logging.DEBUG,
        )


def sub_task(task):
    task.run(commands.command, command="echo {}".format(task.host))


def fail_command_subtask_no_capture(task):
    command = "ls -la /tmp1"
    task.run(task=commands.command, command=command)
    return "I shouldn't be here"


def fail_command_subtask_capture(task):
    command = "ls -la /tmp1"
    try:
        task.run(task=commands.command, command=command)
    except Exception:
        return "I captured this succcessfully"


class Test(object):
    def test_task(self, nornir):
        result = nornir.run(commands.command, command="echo hi")
        assert result
        for h, r in result.items():
            assert r.stdout.strip() == "hi"

    def test_sub_task(self, nornir):
        result = nornir.run(sub_task)
        assert result
        for h, r in result.items():
            assert r[0].name == "sub_task"
            assert r[1].name == "command"
            assert h == r[1].stdout.strip()

    def test_skip_failed_host(self, nornir):
        result = nornir.run(task_fails_for_some)
        assert result.failed
        assert "dev3.group_2" in result

        for h, r in result.items():
            if h == "dev3.group_2":
                assert r.failed
            else:
                assert not r.failed
                assert h == r[1].stdout.strip()

        result = nornir.run(task_fails_for_some)
        assert not result.failed
        assert "dev3.group_2" not in result

    def test_run_on(self, nornir):
        result = nornir.run(task_fails_for_some)
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" in result

        result = nornir.run(task_fails_for_some, on_failed=True)
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" in result

        result = nornir.run(task_fails_for_some, on_failed=True, on_good=False)
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" not in result

        result = nornir.run(task_fails_for_some, on_failed=False, on_good=True)
        assert not result.failed
        assert "dev3.group_2" not in result
        assert "dev1.group_1" in result

    def test_severity(self, nornir):
        r = nornir.run(commands.command, command="echo blah")
        for host, result in r.items():
            assert result[0].severity_level == logging.INFO

        r = nornir.run(
            commands.command, command="echo blah", severity_level=logging.WARN
        )
        for host, result in r.items():
            assert result[0].severity_level == logging.WARN

        r = nornir.run(sub_task, severity_level=logging.WARN)
        for host, result in r.items():
            for sr in result:
                assert sr.severity_level == logging.WARN

        r = nornir.run(task_fails_for_some, severity_level=logging.WARN, num_workers=1)
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result[0].severity_level == logging.ERROR
            else:
                assert result[0].severity_level == logging.WARN
                assert result[1].severity_level == logging.DEBUG

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
        r = host.run(task=fail_command_subtask_no_capture)
        assert r.failed
        assert r["dev1.group_1"][0].exception.__class__ is NornirSubTaskError
        assert r["dev1.group_1"][1].exception.__class__ is CommandError

    def test_subtask_exception_capture(self, nornir):
        host = nornir.filter(name="dev1.group_1")
        r = host.run(task=fail_command_subtask_capture)
        assert r.failed
        assert not r["dev1.group_1"][0].exception
        assert r["dev1.group_1"][0].result == "I captured this succcessfully"
        assert r["dev1.group_1"][1].exception.__class__ is CommandError
