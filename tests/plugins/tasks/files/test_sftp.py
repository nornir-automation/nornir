import uuid

#  from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import files

#  import pytest


class Test(object):

    def test_sftp_put(self, brigade):
        result = brigade.run(files.sftp,
                             dry_run=True,
                             action="put",
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=False,
                             action="put",
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=True,
                             action="put",
                             src="README.md",
                             dst="/tmp/README.md")

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_get(self, brigade):
        filename = "/tmp/" + str(uuid.uuid4()) + "-{host}"
        result = brigade.run(files.sftp,
                             dry_run=True,
                             action="get",
                             src="/etc/hostname",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=False,
                             action="get",
                             src="/etc/hostname",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=False,
                             action="get",
                             src="/etc/hostname",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_put_directory(self, brigade):
        result = brigade.run(files.sftp,
                             dry_run=True,
                             action="put",
                             src="./brigade",
                             dst="/tmp/asd")

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=False,
                             action="put",
                             src="./brigade",
                             dst="/tmp/asd")

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=True,
                             action="put",
                             src="./brigade",
                             dst="/tmp/asd")

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_get_directory(self, brigade):
        filename = "/tmp/" + str(uuid.uuid4()) + "-{host}"
        result = brigade.run(files.sftp,
                             dry_run=True,
                             action="get",
                             src="/etc/terminfo/",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=False,
                             action="get",
                             src="/etc/terminfo/",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(files.sftp,
                             dry_run=True,
                             action="get",
                             src="/etc/terminfo/",
                             dst=filename)

        assert result
        for h, r in result.items():
            assert not r.changed
