from nornir.plugins.tasks.networking import wait_for_connection
from nornir.core.task import AggregatedResult
from tests import skip


class Test(object):
    def test_result(self, nornir):
        result = nornir.run(
            wait_for_connection, port=22, timeout=1, interval=0, delay=0
        )
        assert isinstance(result, AggregatedResult)

    @skip  # This test can be run against inventory hosts which will not respond on TCP port 2222.
    def test_dead_hosts(self, nornir):
        result = nornir.run(
            wait_for_connection, port=2222, timeout=1, interval=0, delay=0
        )
        assert result
        for h, mr in result.items():
            for r in mr:
                assert r.failed is True

    # @skip  # This test can be run against inventory hosts with active TCP port 22
    # def test_online_hosts(self, nornir):
    #     result = nornir.run(
    #         wait_for_connection, port=22, timeout=1, interval=0, delay=0
    #     )
    #     assert result
    #     for h, mr in result.items():
    #         for r in mr:
    #             assert r.failed is False
