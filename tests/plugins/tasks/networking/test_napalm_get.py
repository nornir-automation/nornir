import os

from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.tasks import connections, networking

import pytest


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_get"


class Test(object):

    def test_napalm_getters(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_getters"}
        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(networking.napalm_get,
                       getters=["facts",
                                "interfaces"])
        assert result
        for h, r in result.items():
            assert r.result["facts"]
            assert r.result["interfaces"]

    def test_napalm_getters_error(self, brigade):
        opt = {"path": THIS_DIR + "/test_napalm_getters_error"}
        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)

        with pytest.raises(BrigadeExecutionError) as e:
            d.run(networking.napalm_get,
                  getters=["facts",
                           "interfaces"])
        assert len(e.value.failed_hosts)
        for result in e.value.failed_hosts.values():
            assert isinstance(result.exception, KeyError)
