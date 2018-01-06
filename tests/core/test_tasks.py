from brigade.plugins.tasks import commands


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
