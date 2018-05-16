import os

from nornir.plugins.tasks import connections, networking


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_get"


class Test(object):

    def test_napalm_getters(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(networking.napalm_get, getters=["facts", "interfaces"])
        assert result
        for h, r in result.items():
            assert r.result["facts"]
            assert r.result["interfaces"]

    def test_napalm_getters_error(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters_error"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)

        results = d.run(networking.napalm_get, getters=["facts", "interfaces"])
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, KeyError)
        assert processed
        nornir.data.reset_failed_hosts()
