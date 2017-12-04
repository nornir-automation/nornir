import os

from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.tasks import networking

from napalm.base import exceptions

import pytest


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_configure"


class Test(object):

    def test_napalm_configure_change_dry_run(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_dry_run"}
        configuration = "hostname changed-hostname"
        result = brigade.filter(name="dev3.group_2").run(networking.napalm_configure,
                                                         configuration=configuration,
                                                         optional_args=opt)
        assert result
        for h, r in result.items():
            assert "+hostname changed-hostname" in r.diff
            assert r.changed

    def test_napalm_configure_change_commit(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_commit/step1"}
        configuration = "hostname changed-hostname"
        brigade.dry_run = False
        result = brigade.filter(name="dev3.group_2").run(networking.napalm_configure,
                                                         num_workers=1,
                                                         configuration=configuration,
                                                         optional_args=opt)
        brigade.dry_run = True
        assert result
        for h, r in result.items():
            assert "+hostname changed-hostname" in r.diff
            assert r.changed
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_commit/step2"}
        result = brigade.filter(name="dev3.group_2").run(networking.napalm_configure,
                                                         configuration=configuration,
                                                         optional_args=opt)
        assert result
        for h, r in result.items():
            assert "+hostname changed-hostname" not in r.diff
            assert not r.changed

    def test_napalm_configure_change_error(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_configure_change_error"}
        configuration = "hostname changed_hostname"

        with pytest.raises(BrigadeExecutionError) as e:
            brigade.filter(name="dev3.group_2").run(networking.napalm_configure,
                                                    configuration=configuration,
                                                    optional_args=opt)
        assert len(e.value.failed_hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, exceptions.MergeConfigException)
