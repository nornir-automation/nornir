from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import commands

import pytest


class Test(object):

    def test_command(self, brigade):
        result = brigade.run(commands.command,
                             command="echo {host.name}")
        assert result
        for h, r in result.items():
            assert h == r.stdout.strip()

    def test_command_error(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(commands.command,
                        command="ech")
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for result in e.value.failed_hosts.values():
            assert isinstance(result.exception, OSError)

    def test_command_error_generic(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(commands.command,
                        command="ls /asdadsd")
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for result in e.value.failed_hosts.values():
            assert isinstance(result.exception, CommandError)
