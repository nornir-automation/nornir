import os

from nornir.plugins.tasks import networking


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_rollback"


def connect(task, extras):
    if "napalm" in task.host.connections:
        task.host.close_connection("napalm")
    task.host.open_connection(
        "napalm",
        task.nornir.config,
        extras={"optional_args": extras},
        default_to_host_attributes=True,
    )


class Test(object):
    def test_napalm_rollback_commit(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_rollback_commit"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connect, extras=opt)
        result = d.run(
            networking.napalm_rollback, dry=False, configuration=configuration
        )
        assert result
        for h, r in result.items():
            # Need to figure out what if a diff is returned
            assert r.changed

    def test_napalm_rollback_dry_run(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_rollback_dry_run"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connect, extras=opt)
        result = d.run(
            networking.napalm_rollback, dry=True, configuration=configuration
        )
        assert result
        for h, r in result.items():
            # Need to figure out what if a diff is returned
            assert not r.changed
