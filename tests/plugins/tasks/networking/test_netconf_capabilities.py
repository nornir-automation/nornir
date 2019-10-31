from nornir.plugins.tasks import networking


def test_netconf_capabilities(netconf):
    result = netconf.run(networking.netconf_capabilities)

    for _, v in result.items():
        assert "urn:ietf:params:netconf:capability:writable-running:1.0" in v.result
