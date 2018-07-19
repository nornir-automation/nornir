import os


from nornir.core import Nornir
from nornir.plugins.inventory.simple import SimpleInventory
from nornir.plugins.tasks import networking


cur_dir = os.path.dirname(os.path.realpath(__file__))
ext_inv_file = "{}/../../../inventory_data/external_hosts.yaml".format(cur_dir)


class Test(object):
    def test_tcp_ping_port(self, nornir):
        filter = nornir.filter(name="dev4.group_2")
        result = filter.run(networking.tcp_ping, ports=65004)

        assert result
        for h, r in result.items():
            assert r.result[65004]

    def test_tcp_ping_ports(self, nornir):
        filter = nornir.filter(name="dev4.group_2")
        result = filter.run(networking.tcp_ping, ports=[35004, 65004])

        assert result
        for h, r in result.items():
            assert r.result[35004] is False
            assert r.result[65004]

    def test_tcp_ping_invalid_port(self, nornir):
        results = nornir.run(networking.tcp_ping, ports="web")
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, ValueError)
        assert processed
        nornir.data.reset_failed_hosts()

    def test_tcp_ping_invalid_ports(self, nornir):
        results = nornir.run(networking.tcp_ping, ports=[22, "web", 443])
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, ValueError)
        assert processed
        nornir.data.reset_failed_hosts()


def test_tcp_ping_external_hosts():
    external = Nornir(inventory=SimpleInventory(ext_inv_file, ""), dry_run=True)
    result = external.run(networking.tcp_ping, ports=[23, 443])

    assert result
    for h, r in result.items():
        if h == "www.github.com":
            assert r.result[23] is False
            assert r.result[443]
        else:
            assert r.result[23] is False
            assert r.result[443] is False
