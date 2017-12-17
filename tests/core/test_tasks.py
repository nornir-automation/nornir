from brigade.plugins.tasks import commands


def task_fails_for_some(task):
    if task.host.name == "dev3.group_2":
        # let's hardcode a failure
        return task.run(commands.command,
                        command="sasdasdasd")
    else:
        return task.run(commands.command,
                        command="echo {}".format(task.host))


def sub_task(task):
    return task.run(commands.command,
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
            assert h == r.stdout.strip()

    def test_skip_failed_host(self, brigade):
        brigade.config.raise_on_error = False
        result = brigade.run(task_fails_for_some)
        for h, r in result.items():
            assert h == r.stdout.strip()

        # We can set it to True already because the task
        # shouldn't be run on the host that fails
        brigade.config.raise_on_error = True

        result = brigade.run(task_fails_for_some)
        for h, r in result.items():
            if h == "dev3.group_2":
                assert r.skipped
            else:
                assert h == r.stdout.strip()

        # let's reset it
        brigade.data.failed_hosts = set()
