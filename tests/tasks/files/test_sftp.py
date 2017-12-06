import uuid

#  from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import files

#  import pytest


class Test(object):

    def test_sftp_put(self, brigade):
        brigade.dry_run = True
        result = brigade.run(files.sftp,
                             action="put",
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert r.changed

        brigade.dry_run = False
        result = brigade.run(files.sftp,
                             action="put",
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert r.changed

        brigade.dry_run = True
        result = brigade.run(files.sftp,
                             action="put",
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_get(self, brigade):
        filename = "/tmp/{host}-" + str(uuid.uuid4())
        brigade.dry_run = True
        result = brigade.run(files.sftp,
                             action="get",
                             src="/etc/hostname",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert r.changed

        brigade.dry_run = False
        result = brigade.run(files.sftp,
                             action="get",
                             src="/etc/hostname",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert r.changed

        brigade.dry_run = True
        result = brigade.run(files.sftp,
                             action="get",
                             src="/etc/hostname",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert not r.changed
