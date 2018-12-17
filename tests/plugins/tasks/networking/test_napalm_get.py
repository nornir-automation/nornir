import os

from nornir.plugins.tasks import networking


THIS_DIR = os.path.dirname(os.path.realpath(__file__)) + "/mocked/napalm_get"


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
    def test_napalm_getters(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters"}
        d = nornir.filter(name="dev3.group_2")
        d.run(task=connect, extras=opt)
        result = d.run(networking.napalm_get, getters=["facts", "interfaces"])
        assert result
        for h, r in result.items():
            assert r.result["facts"]
            assert r.result["interfaces"]

    def test_napalm_getters_error(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters_error"}
        d = nornir.filter(name="dev3.group_2")
        d.run(task=connect, extras=opt)

        results = d.run(networking.napalm_get, getters=["facts", "interfaces"])
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, KeyError)
        assert processed

    def test_napalm_getters_with_options_error(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters_single_with_options"}
        d = nornir.filter(name="dev3.group_2")
        d.run(task=connect, extras=opt)
        result = d.run(
            task=networking.napalm_get, getters=["config"], nonexistent="asdsa"
        )
        assert result
        assert result.failed
        for h, r in result.items():
            assert "unexpected keyword argument 'nonexistent'" in r.result

    def test_napalm_getters_with_options_error_optional_args(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters_single_with_options"}
        d = nornir.filter(name="dev3.group_2")
        d.run(task=connect, extras=opt)
        result = d.run(
            task=networking.napalm_get,
            getters=["config"],
            getters_options={"config": {"nonexistent": "asdasd"}},
        )
        assert result
        assert result.failed
        for h, r in result.items():
            assert "unexpected keyword argument 'nonexistent'" in r.result

    def test_napalm_getters_single_with_options(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters_single_with_options"}
        d = nornir.filter(name="dev3.group_2")
        d.run(task=connect, extras=opt)
        result = d.run(
            task=networking.napalm_get, getters=["config"], retrieve="candidate"
        )
        assert result
        assert not result.failed
        for h, r in result.items():
            assert r.result["config"]

    def test_napalm_getters_multiple_with_options(self, nornir):
        opt = {"path": THIS_DIR + "/test_napalm_getters_multiple_with_options"}
        d = nornir.filter(name="dev3.group_2")
        d.run(task=connect, extras=opt)
        result = d.run(
            task=networking.napalm_get,
            getters=["config", "facts"],
            getters_options={"config": {"retrieve": "candidate"}},
        )
        assert result
        assert not result.failed
        for h, r in result.items():
            assert r.result["config"]
            assert r.result["facts"]
