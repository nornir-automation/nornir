import os

from brigade.plugins.tasks import connections, networking


THIS_DIR = os.path.dirname(os.path.realpath(__file__))


class Test(object):

    def test_napalm_validate_src_ok(self, brigade):
        opt = {"path": THIS_DIR + "/mocked/napalm_get/test_napalm_getters"}
        print(opt["path"])
        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(networking.napalm_validate,
                       src=THIS_DIR + "/data/validate_ok.yaml")
        assert result
        for h, r in result.items():
            assert not r.failed

    def test_napalm_validate_src_error(self, brigade):
        opt = {"path": THIS_DIR + "/mocked/napalm_get/test_napalm_getters"}
        print(opt["path"])
        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)
        result = d.run(networking.napalm_validate,
                       src=THIS_DIR + "/data/validate_error.yaml")
        assert result
        for h, r in result.items():
            assert r.failed
            assert not r.result["complies"]

    def test_napalm_validate_src_validate_source(self, brigade):
        opt = {"path": THIS_DIR + "/mocked/napalm_get/test_napalm_getters"}
        print(opt["path"])
        d = brigade.filter(name="dev3.group_2")
        d.run(connections.napalm_connection, optional_args=opt)

        validation_dict = [
                {"get_interfaces": {"Ethernet1": {"description": ""}}}
        ]

        result = d.run(networking.napalm_validate,
                       validation_source=validation_dict)

        assert result
        for h, r in result.items():
            assert not r.failed
