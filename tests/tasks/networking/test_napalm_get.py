import os

from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.tasks import networking

import pytest


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_get"


class Test(object):

    def test_napalm_getters(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_getters"}
        result = brigade.filter(name="dev3.group_2").run(networking.napalm_get,
                                                         getters=["facts",
                                                                  "interfaces"],
                                                         optional_args=opt)
        assert result
        for h, r in result.items():
            assert r.result["facts"]
            assert r.result["interfaces"]

    def test_napalm_getters_error(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_getters_error"}

        with pytest.raises(BrigadeExecutionError) as e:
            brigade.filter(name="dev3.group_2").run(networking.napalm_get,
                                                    getters=["facts",
                                                             "interfaces"],
                                                    optional_args=opt)
        assert len(e.value.failed_hosts)
        for exc in e.value.failed_hosts.values():
            assert isinstance(exc, KeyError)
