import os


from brigade.core import Brigade
from brigade.core.exceptions import BrigadeExecutionError
from brigade.plugins.inventory.simple import SimpleInventory
from brigade.plugins.tasks import networking


import pytest

cur_dir = os.path.dirname(os.path.realpath(__file__))
ext_inv_file = '{}/../../../inventory_data/external_hosts.yaml'.format(cur_dir)


class Test(object):

    def test_tcp_ping_port(self, brigade):
        filter = brigade.filter(name="dev4.group_2")
        result = filter.run(networking.tcp_ping, ports=65004)

        assert result
        for h, r in result.items():
            assert r.tcp_port[65004]

    def test_tcp_ping_ports(self, brigade):
        filter = brigade.filter(name="dev4.group_2")
        result = filter.run(networking.tcp_ping, ports=[35004, 65004])

        assert result
        for h, r in result.items():
            assert r.tcp_port[35004] is False
            assert r.tcp_port[65004]

    def test_tcp_ping_invalid_port(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(networking.tcp_ping,
                        ports='web')
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for result in e.value.failed_hosts.values():
            assert isinstance(result.exception, ValueError)

    def test_tcp_ping_invalid_ports(self, brigade):
        with pytest.raises(BrigadeExecutionError) as e:
            brigade.run(networking.tcp_ping,
                        ports=[22, 'web', 443])
        assert len(e.value.failed_hosts) == len(brigade.inventory.hosts)
        for result in e.value.failed_hosts.values():
            assert isinstance(result.exception, ValueError)


def test_tcp_ping_external_hosts():
    external = Brigade(inventory=SimpleInventory(ext_inv_file), dry_run=True)
    result = external.run(networking.tcp_ping, ports=[23, 443])

    assert result
    for h, r in result.items():
        if h == 'www.github.com':
            assert r.tcp_port[23] is False
            assert r.tcp_port[443]
        else:
            assert r.tcp_port[23] is False
            assert r.tcp_port[443] is False
