from unittest import mock

from nornir.core.task import Result
from nornir.plugins.functions.stream.kafka import send_result


def simple_task(task):
    return Result(task.host if task else None, result="Task result")


def multi_task(task):
    task.run(simple_task)


@mock.patch("nornir.plugins.functions.stream.kafka.kafka.KafkaProducer")
class Test(object):
    def test_kafka_send_result(self, producer, nornir):
        filter = nornir.filter(name="dev1.group_1")
        result = filter.run(simple_task)
        send_result(result["dev1.group_1"][0], "my topic", "broker:9000")
        assert producer.return_value.send.call_count == 1
        assert producer.return_value.send.call_args[1]["key"] == "dev1.group_1"
        assert (
            producer.return_value.send.call_args[1]["value"]
            == result["dev1.group_1"][0]
        )

    def test_kafka_send_multiresult(self, producer, nornir):
        filter = nornir.filter(name="dev1.group_1")
        result = filter.run(multi_task)
        send_result(result["dev1.group_1"], "my topic", "broker:9000")
        assert producer.return_value.send.call_count == 2

    def test_kafka_send_aggregateresult(self, producer, nornir):
        filter = nornir.filter(role="www")
        result = filter.run(simple_task)
        send_result(result, "my topic", "broker:9000")
        assert producer.return_value.send.call_count == 2

    def test_kafka_send_result_with_key(self, producer, nornir):
        filter = nornir.filter(name="dev1.group_1")
        result = filter.run(simple_task)
        send_result(result, "my topic", "broker:9000", key="my key")
        assert producer.return_value.send.call_args[1]["key"] == "my key"
