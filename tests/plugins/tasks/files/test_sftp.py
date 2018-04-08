import uuid

#  from brigade.core.exceptions import BrigadeExecutionError, CommandError
from brigade.plugins.tasks import files

#  import pytest


def get_file(task):
    filename = "/tmp/{uuid}-{host.name}".format(uuid=uuid.uuid4(), host=task.host)
    r = task.run(
        task=files.sftp, dry_run=True, action="get", src="/etc/hostname", dst=filename
    )
    assert r
    assert r.changed, r.files_changed

    r = task.run(
        task=files.sftp, dry_run=False, action="get", src="/etc/hostname", dst=filename
    )
    assert r
    assert r.changed, r.files_changed

    r = task.run(
        task=files.sftp, dry_run=False, action="get", src="/etc/hostname", dst=filename
    )
    assert r
    assert not r.changed


def get_directory(task):
    filename = "/tmp/{uuid}-{host.name}".format(uuid=uuid.uuid4(), host=task.host)
    r = task.run(
        task=files.sftp, dry_run=True, action="get", src="/etc/terminfo/", dst=filename
    )
    assert r
    assert r.changed, r.files_changed

    r = task.run(
        task=files.sftp, dry_run=False, action="get", src="/etc/terminfo/", dst=filename
    )
    assert r
    assert r.changed, r.files_changed

    r = task.run(
        task=files.sftp, dry_run=True, action="get", src="/etc/terminfo/", dst=filename
    )
    assert r
    assert not r.changed


class Test(object):

    def test_sftp_put(self, brigade):
        result = brigade.run(
            files.sftp,
            dry_run=True,
            action="put",
            src="README.md",
            dst="/tmp/README.md",
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(
            files.sftp,
            dry_run=False,
            action="put",
            src="README.md",
            dst="/tmp/README.md",
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(
            files.sftp,
            dry_run=True,
            action="put",
            src="README.md",
            dst="/tmp/README.md",
        )

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_get(self, brigade):
        result = brigade.run(get_file)
        assert not result.failed

    def test_sftp_put_directory(self, brigade):
        result = brigade.run(
            files.sftp, dry_run=True, action="put", src="./brigade", dst="/tmp/asd"
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(
            files.sftp, dry_run=False, action="put", src="./brigade", dst="/tmp/asd"
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(
            files.sftp, dry_run=True, action="put", src="./brigade", dst="/tmp/asd"
        )

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_get_directory(self, brigade):
        filename = "/tmp/" + str(uuid.uuid4()) + "-{host}"
        result = brigade.run(
            files.sftp, dry_run=True, action="get", src="/etc/terminfo/", dst=filename
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(
            files.sftp, dry_run=False, action="get", src="/etc/terminfo/", dst=filename
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = brigade.run(
            files.sftp, dry_run=True, action="get", src="/etc/terminfo/", dst=filename
        )

        assert result
        for h, r in result.items():
            assert not r.changed
