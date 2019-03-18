import uuid

#  from nornir.core.exceptions import NornirExecutionError, CommandError
from nornir.plugins.tasks import files

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
    def test_sftp_put(self, nornir):
        u = uuid.uuid4()
        result = nornir.run(
            files.sftp,
            dry_run=True,
            action="put",
            src="README.md",
            dst=f"/tmp/README-{u}.md",
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = nornir.run(
            files.sftp,
            dry_run=False,
            action="put",
            src="README.md",
            dst=f"/tmp/README-{u}.md",
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = nornir.run(
            files.sftp,
            dry_run=True,
            action="put",
            src="README.md",
            dst=f"/tmp/README-{u}.md",
        )

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_get(self, nornir):
        result = nornir.run(get_file)
        assert not result.failed

    def test_sftp_put_directory(self, nornir):
        u = uuid.uuid4()
        result = nornir.run(
            files.sftp, dry_run=True, action="put", src="./nornir", dst=f"/tmp/{u}"
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = nornir.run(
            files.sftp, dry_run=False, action="put", src="./nornir", dst=f"/tmp/{u}"
        )

        assert result
        for h, r in result.items():
            assert r.changed, r.files_changed

        result = nornir.run(
            files.sftp, dry_run=True, action="put", src="./nornir", dst=f"/tmp/{u}"
        )

        assert result
        for h, r in result.items():
            assert not r.changed

    def test_sftp_get_directory(self, nornir):
        result = nornir.run(get_directory)
        assert not result.failed
