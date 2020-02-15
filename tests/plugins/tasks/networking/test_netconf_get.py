from nornir.plugins.tasks import networking


def test_netconf_get(netconf):
    result = netconf.run(networking.netconf_get)

    for _, v in result.items():
        assert "<turing-machine" in v.result


def test_netconf_get_subtree(netconf):
    result = netconf.run(
        networking.netconf_get,
        path="<turing-machine></turing-machine>",
        filter_type="subtree",
    )

    for _, v in result.items():
        assert "<turing-machine" in v.result
