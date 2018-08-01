from unittest import mock

from nornir.plugins.tasks import networking

#@mock.patch('ConnectHandler')
#def mock_simple_function():
#from Netmiko import ConnectHandler



class Test(object):
    def test_netmiko_conn(self, nornir_conn_tests):

        test_args = {
            'device_type': 'linux',
            'host': '127.0.0.1',
            'username': 'root',
            'password': 'docker',
            'port': 65004,
        }

        nornir_dev4 = nornir_conn_tests.filter(name="dev4.group_2")
        result = nornir_dev4.run(
            networking.netmiko_send_command, command_string="hostname"
        )

        netmiko_conn = nornir_dev4.inventory.hosts['dev4.group_2'].get_connection('netmiko')
        netmiko_args = netmiko_conn.__dict__
        for k, v in test_args.items():
            assert netmiko_args[k] == v
        assert netmiko_args['device_type'] == 'linux'
        assert netmiko_args['host'] == '127.0.0.1'
        assert netmiko_args['username'] == 'root'
        assert netmiko_args['password'] == 'docker'
        assert netmiko_args['port'] == 65004
        assert netmiko_args['remote_conn'] is not None

        nornir_dev4 = nornir_conn_tests.filter(name="dev5.group_2")
        result = nornir_dev4.run(
            networking.netmiko_send_command, command_string="hostname"
        )

        netmiko_conn = nornir_dev4.inventory.hosts['dev5.group_2'].get_connection('netmiko')
        netmiko_args = netmiko_conn.__dict__
        assert netmiko_args['device_type'] == 'linux'
        assert netmiko_args['host'] == '127.0.0.1'
        assert netmiko_args['username'] == 'root'
        assert netmiko_args['password'] == 'docker'
        assert netmiko_args['port'] == 65004
        assert netmiko_args['remote_conn'] is not None

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
