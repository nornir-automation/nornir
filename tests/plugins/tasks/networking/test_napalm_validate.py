import os

from nornir.plugins.tasks import networking


THIS_DIR = os.path.dirname(os.path.realpath(__file__))


def connect(task, connection_options):
    if "napalm" in task.host.connections:
        task.host.close_connection("napalm")
    task.host.open_connection(
        "napalm", connection_options=connection_options, default_to_host_attributes=True
    )


class Test(object):
    def test_napalm_validate_src_ok(self, nornir):
        opt = {"path": THIS_DIR + "/mocked/napalm_get/test_napalm_getters"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connect, connection_options=opt)
        result = d.run(
            networking.napalm_validate, src=THIS_DIR + "/data/validate_ok.yaml"
        )
        assert result
        for h, r in result.items():
            assert not r.failed

    def test_napalm_validate_src_error(self, nornir):
        opt = {"path": THIS_DIR + "/mocked/napalm_get/test_napalm_getters"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connect, connection_options=opt)

        result = d.run(
            networking.napalm_validate, src=THIS_DIR + "/data/validate_error.yaml"
        )
        assert result
        for h, r in result.items():
            assert not r.failed
            assert not r.result["complies"]

    def test_napalm_validate_src_validate_source(self, nornir):
        opt = {"path": THIS_DIR + "/mocked/napalm_get/test_napalm_getters"}
        d = nornir.filter(name="dev3.group_2")
        d.run(connect, connection_options=opt)

        validation_dict = [{"get_interfaces": {"Ethernet1": {"description": ""}}}]

        result = d.run(networking.napalm_validate, validation_source=validation_dict)

        assert result
        for h, r in result.items():
            assert not r.failed
            assert r.result["complies"]
