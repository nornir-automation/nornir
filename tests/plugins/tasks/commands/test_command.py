from nornir.core.exceptions import CommandError
from nornir.plugins.tasks import commands


def echo_hostname(task):
    command = "echo {host.name}".format(host=task.host)
    task.run(task=commands.command, command=command)


class Test(object):
    def test_command(self, nornir):
        result = nornir.run(echo_hostname)
        assert result
        for h, r in result.items():
            assert h == r[1].stdout.strip()

    def test_command_error(self, nornir):
        result = nornir.run(commands.command, command="ech")
        processed = False
        for r in result.values():
            processed = True
            assert isinstance(r.exception, OSError)
        assert processed

    def test_command_error_generic(self, nornir):
        result = nornir.run(commands.command, command="ls /asdadsd")
        processed = False
        for r in result.values():
            processed = True
            assert isinstance(r.exception, CommandError)
        assert processed
