from nornir.plugins.tasks import networking


class Test(object):
    def test_netmiko_conn(self, nornir_conn_tests):

        test_args = {
            'device_type': 'linux',
            'host': '127.0.0.1',
            'username': 'root',
            'password': 'docker',
            'port': 65004,
        }

        test_hosts = ["dev4.group_2", "dev5.group_2"]
        for nornir_host in test_hosts:
            nornir_obj = nornir_conn_tests.filter(name=nornir_host)
            nornir_obj.run(
                networking.netmiko_send_command, command_string="hostname"
            )

            netmiko_conn = nornir_obj.inventory.hosts[nornir_host].get_connection('netmiko')
            for k, v in test_args.items():
                assert getattr(netmiko_conn, k) == v
            assert netmiko_conn.remote_conn is not None

            # Close the Netmiko connections
            nornir_obj.inventory.hosts[nornir_host].close_connection("netmiko")
            assert nornir_obj.inventory.hosts[nornir_host].connections == {}

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
