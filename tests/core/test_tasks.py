import logging

from brigade.plugins.tasks import commands


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


class Test(object):

    def test_task(self, brigade):
        result = brigade.run(commands.command, command="echo hi")
        assert result
        for h, r in result.items():
            assert r.stdout.strip() == "hi"

    def test_sub_task(self, brigade):
        result = brigade.run(sub_task)
        assert result
        for h, r in result.items():
            assert r[0].name == "sub_task"
            assert r[1].name == "command"
            assert h == r[1].stdout.strip()

    def test_skip_failed_host(self, brigade):
        result = brigade.run(task_fails_for_some)
        assert result.failed
        assert "dev3.group_2" in result

        for h, r in result.items():
            if h == "dev3.group_2":
                assert r.failed
            else:
                assert not r.failed
                assert h == r[1].stdout.strip()

        result = brigade.run(task_fails_for_some)
        assert not result.failed
        assert "dev3.group_2" not in result

        brigade.data.reset_failed_hosts()

    def test_run_on(self, brigade):
        result = brigade.run(task_fails_for_some)
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" in result

        result = brigade.run(task_fails_for_some, on_failed=True)
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" in result

        result = brigade.run(task_fails_for_some, on_failed=True, on_good=False)
        assert result.failed
        assert "dev3.group_2" in result
        assert "dev1.group_1" not in result

        result = brigade.run(task_fails_for_some, on_failed=False, on_good=True)
        assert not result.failed
        assert "dev3.group_2" not in result
        assert "dev1.group_1" in result

        brigade.data.reset_failed_hosts()

    def test_severity(self, brigade):
        r = brigade.run(commands.command, command="echo blah")
        for host, result in r.items():
            assert result[0].severity_level == logging.INFO

        r = brigade.run(
            commands.command, command="echo blah", severity_level=logging.WARN
        )
        for host, result in r.items():
            assert result[0].severity_level == logging.WARN

        r = brigade.run(sub_task, severity_level=logging.WARN)
        for host, result in r.items():
            for sr in result:
                assert sr.severity_level == logging.WARN

        r = brigade.run(task_fails_for_some, severity_level=logging.WARN, num_workers=1)
        for host, result in r.items():
            if host == "dev3.group_2":
                assert result[0].severity_level == logging.ERROR
            else:
                assert result[0].severity_level == logging.WARN
                assert result[1].severity_level == logging.DEBUG

        brigade.data.reset_failed_hosts()
