from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import commands
from brigade.plugins.tasks import files

import pytest


class Test(object):

    def test_scp(self, brigade):
        brigade.run(files.scp,
                    src="README.md",
                    dst="{host.host}:/tmp")

        # let's check the file is there
        result = brigade.run(commands.remote_command,
                             command="ls /tmp/README.md")
        assert result
        for h, r in result.items():
            assert r.stdout == "/tmp/README.md\n"

    def test_scp_error_generic(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(files.scp,
                        src="README.md",
                        dst="{host.host}:/asdasd/tmp")
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, CommandError)
