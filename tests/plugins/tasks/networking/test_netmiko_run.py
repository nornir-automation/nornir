from brigade.plugins.tasks import networking


class Test(object):

    def test_netmiko_run(self, brigade):
        result = brigade.filter(name="dev4.group_2").run(networking.netmiko_run,
                                                         method="send_command",
                                                         command_string="hostname")
        assert result
        for h, r in result.items():
            assert h == r.result.strip()
