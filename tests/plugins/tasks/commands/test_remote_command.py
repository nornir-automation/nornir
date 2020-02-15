from nornir.core.exceptions import CommandError
from nornir.plugins.tasks import commands


class Test(object):
    def test_remote_command(self, nornir):
        result = nornir.run(commands.remote_command, command="hostname")
        assert result
        for h, r in result.items():
            assert h == r.stdout.strip()

    def test_remote_command_error_generic(self, nornir):
        result = nornir.run(commands.remote_command, command="ls /asdadsd")
        processed = False
        for r in result.values():
            processed = True
            assert isinstance(r.exception, CommandError)
        assert processed
