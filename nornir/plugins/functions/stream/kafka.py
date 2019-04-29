from typing import Any, Callable, Iterable, Optional, Mapping, Union

import json
import threading

import kafka

from nornir.core.task import AggregatedResult, MultiResult, Result


LOCK = threading.Lock()


def default_key_serializer(key: Any) -> bytes:
    return str(key).encode("utf-8")


def default_value_serializer(result: Result) -> bytes:
    d = {
        k: v if isinstance(v, (dict, str)) else str(v) for k, v in vars(result).items()
    }
    j = json.dumps(d)
    return j.encode("utf-8")


def _send_single_result(
    result: Result, p: kafka.KafkaProducer, topic: str, key: Optional[Any]
) -> None:
    key = key or result.host.name
    p.send(topic, value=result, key=key)


def _send_result(
    result: Result, p: kafka.KafkaProducer, topic: str, key: Optional[Any]
) -> None:
    if isinstance(result, AggregatedResult):
        for h in result.values():
            for r in h:
                _send_single_result(r, p, topic, key)
    elif isinstance(result, MultiResult):
        for r in result:
            _send_single_result(r, p, topic, key)
    elif isinstance(result, Result):
        _send_single_result(result, p, topic, key)


def send_result(
    result: Result,
    topic: str,
    bootstrap_servers: Union[Iterable[str], str],
    key: Optional[Any] = None,
    key_serializer: Optional[Callable[[Any], bytes]] = default_key_serializer,
    value_serializer: Optional[Callable[[Result], bytes]] = default_value_serializer,
    **kwargs: Mapping[str, Any],
) -> None:
    """
    Send the :obj:`nornir.core.task.Result` from a previous task to the Kafka cluster specified by
    the bootstrap server[s]

    Arguments:
        result: (:obj:`nornir.core.task.Result`)
        topic (``str``): Topic to send on
        bootstrap_servers (``str`` or ``[str, ...]``: Kafka brokers to bootstrap from
        key: Key for the message, default the name of the :obj:`nornir.core.inventory.Host`
        key_serializer: (``callable``): Function to serialize key to bytes.  Default is UTF-8
        value_serializer (``callable``): Function to serialize result value to bytes.  Default is
           a JSON dump of the result object, with objects de-referenced.
        **kwargs: keyword args to pass into :obj:`kafka.producer.kafka.KafkaProducer`
    """

    key_serializer = key_serializer or default_key_serializer
    value_serializer = value_serializer or default_value_serializer

    with LOCK:
        p = kafka.KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            key_serializer=key_serializer,
            value_serializer=value_serializer,
            **kwargs,
        )
        _send_result(result, p, topic, key)
        p.flush()
