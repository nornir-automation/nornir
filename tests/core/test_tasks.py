from brigade.plugins.tasks import commands


def task_fails_for_some(task):
    if task.host.name == "dev3.group_2":
        # let's hardcode a failure
        task.run(commands.command,
                 command="sasdasdasd")
    else:
        task.run(commands.command,
                 command="echo {}".format(task.host))


def sub_task(task):
    task.run(commands.command,
             command="echo {}".format(task.host))


class Test(object):

    def test_task(self, brigade):
        result = brigade.run(commands.command,
                             command="echo hi")
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
