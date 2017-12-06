#  from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import files

#  import pytest


class Test(object):

    def test_scp(self, brigade):
        brigade.dry_run = True
        result = brigade.run(files.scp,
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert r.changed

        brigade.dry_run = False
        result = brigade.run(files.scp,
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert r.changed

        brigade.dry_run = True
        result = brigade.run(files.scp,
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert not r.changed
