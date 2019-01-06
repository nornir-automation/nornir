from nornir.plugins.tasks import networking


class Test(object):
    def test_tcp_ping_port(self, nornir):
        filter = nornir.filter(name="dev4.group_2")
        result = filter.run(networking.tcp_ping, ports=22)

        assert result
        for h, r in result.items():
            assert r.result[22]

    def test_tcp_ping_ports(self, nornir):
        filter = nornir.filter(name="dev4.group_2")
        result = filter.run(networking.tcp_ping, ports=[35004, 22])

        assert result
        for h, r in result.items():
            assert r.result[35004] is False
            assert r.result[22]

    def test_tcp_ping_invalid_port(self, nornir):
        results = nornir.run(networking.tcp_ping, ports="web")
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, ValueError)
        assert processed

    def test_tcp_ping_invalid_ports(self, nornir):
        results = nornir.run(networking.tcp_ping, ports=[22, "web", 443])
        processed = False
        for result in results.values():
            processed = True
            assert isinstance(result.exception, ValueError)
        assert processed
