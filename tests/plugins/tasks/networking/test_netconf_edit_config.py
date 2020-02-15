from nornir.plugins.tasks import networking
from tests import skip

CONFIG = """
<nc:config
    xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <turing-machine
        xmlns="http://example.net/turing-machine">
        <transition-function>
            <delta nc:operation="{operation}">
                <label>this-is-nornir</label>
                <input>
                    <symbol>4</symbol>
                    <state>1</state>
                </input>
            </delta>
        </transition-function>
    </turing-machine>
</nc:config>
"""


@skip
def test_netconf_edit_config(netconf):
    result = netconf.run(networking.netconf_get_config)

    for _, v in result.items():
        assert "nornir" not in v.result

    netconf.run(networking.netconf_edit_config, config=CONFIG.format(operation="merge"))

    result = netconf.run(networking.netconf_get_config)

    for _, v in result.items():
        assert "nornir" in v.result

    netconf.run(
        networking.netconf_edit_config, config=CONFIG.format(operation="delete")
    )

    result = netconf.run(networking.netconf_get_config)

    for _, v in result.items():
        assert "nornir" not in v.result
