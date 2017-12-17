import os

from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.tasks import connections, networking

from napalm.base import exceptions

import pytest


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_configure"


class Test(object):

    def test_napalm_configure_change_dry_run(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_dry_run"}
        configuration = "hostname changed-hostname"
        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(networking.napalm_configure, configuration=configuration)
        assert result
        for h, r in result.items():
            assert "+hostname changed-hostname" in r.diff
            assert r.changed

    def test_napalm_configure_change_commit(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_commit/step1"}
        configuration = "hostname changed-hostname"
        brigade.dry_run = False
        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(networking.napalm_configure, configuration=configuration)
        d.dry_run = True
        assert result
        for h, r in result.items():
            assert "+hostname changed-hostname" in r.diff
            assert r.changed
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_commit/step2"}
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(networking.napalm_configure, configuration=configuration)
        assert result
        for h, r in result.items():
            assert "+hostname changed-hostname" not in r.diff
            assert not r.changed

    def test_napalm_configure_change_error(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_error"}
        configuration = "hostname changed_hostname"

        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        with pytest.raises(BrigadeExecutionError) as e:
            d.run(networking.napalm_configure, configuration=configuration)
        assert len(e.value.failed_hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, exceptions.MergeConfigException)
