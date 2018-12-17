from nornir.plugins.tasks import networking


class Test(object):
    def test_netmiko_send_command(self, nornir):
        result = nornir.filter(name="dev4.group_2").run(
            networking.netmiko_send_command, command_string="hostname"
        )
        assert result
        for h, r in result.items():
            assert h == r.result.strip()

        result = nornir.filter(name="dev4.group_2").run(
            networking.netmiko_send_command, command_string="hostname", use_timing=True
        )
        assert result
        for h, r in result.items():
            assert h == r.result.strip()
