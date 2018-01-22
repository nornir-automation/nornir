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
        result = brigade.run(task_fails_for_some, raise_on_error=False)
        assert result.failed
        assert not result.skipped
        for h, r in result.items():
            if h == "dev3.group_2":
                assert r.failed
            else:
                assert not r.failed
                assert h == r[1].stdout.strip()

        result = brigade.run(task_fails_for_some)
        assert not result.failed
        assert result.skipped
        for h, r in result.items():
            if h == "dev3.group_2":
                assert r.skipped
            else:
                assert not r.skipped
                assert h == r[1].stdout.strip()

        # let's reset it
        brigade.data.failed_hosts = set()
