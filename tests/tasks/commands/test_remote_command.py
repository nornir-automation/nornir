from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import commands

import pytest


class Test(object):

    def test_remote_command(self, brigade):
        result = brigade.run(commands.remote_command,
                             command="hostname")
        assert result
        for h, r in result.items():
            assert h == r.stdout.strip()

    def test_remote_command_error_generic(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(commands.remote_command,
                        command="ls /asdadsd")
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, CommandError)
