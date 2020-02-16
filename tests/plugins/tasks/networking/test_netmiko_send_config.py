from nornir.plugins.tasks import networking


class Test(object):
    def test_netmiko_send_command(self, nornir):
        result = nornir.filter(name="dev4.group_2").run(
            networking.netmiko_send_config, config_commands="hostname"
        )
        assert result
        for h, r in result.items():
            assert h in r.result.strip()
