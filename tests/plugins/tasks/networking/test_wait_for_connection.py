from nornir.plugins.tasks.networking import wait_for_connection
from nornir.core.task import AggregatedResult
from tests import skip


class Test(object):
    @skip
    def test_dead_hosts(self, nornir):
        filter = nornir.filter(name="dev4.group_2")
        result = filter.run(
            wait_for_connection, port=35004, timeout=1, interval=0, delay=0
        )
        assert isinstance(result, AggregatedResult)
        for h, r in result.items():
            assert r.failed is True

    # @skip
    # def test_online_hosts(self, nornir):
    #     filter = nornir.filter(name="dev4.group_2")
    #     result = filter.run(
    #         wait_for_connection, port=22, timeout=1, interval=0, delay=0
    #     )
    #     assert isinstance(result, AggregatedResult)
    #     for h, r in result.items():
    #         assert r.failed is False
