from nornir.plugins.tasks import networking
from tests import skip


@skip
def test_netconf_get_config(netconf):
    result = netconf.run(networking.netconf_get_config, source="startup")

    for _, v in result.items():
        assert "<turing-machine" in v.result


@skip
def test_netconf_get_config_subtree(netconf):
    result = netconf.run(
        networking.netconf_get_config,
        source="startup",
        path="<interfaces></interfaces>",
        filter_type="subtree",
    )

    for _, v in result.items():
        assert "<interface" in v.result
