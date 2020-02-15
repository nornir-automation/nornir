import socket
import time
from datetime import datetime, timedelta
from typing import Union

from nornir.core.task import Result, Task
from nornir.core.inventory import Host


class TimedOut(Exception):
    pass


def wait_for_connection(
    task: Task,
    port: int,
    delay: int = 0,
    timeout: int = 600,
    interval: int = 1,
    host: Union[str, Host] = None,
) -> Result:
    """
    Wait for connection on a tcp port.
    Args:
        task: Task object
        port: TCP port
        delay: time before start polling a device
        timeout: timeout after a node will be marked as fail
        interval: time between polls
        host: hostname or ip address

    Returns:
        Result object

    """
    host = host or task.host
    end_time = datetime.now() + timedelta(seconds=timeout) + timedelta(seconds=delay)
    time.sleep(delay)
    while datetime.now() < end_time:
        s = socket.socket()
        s.settimeout(5)
        try:
            status = s.connect_ex((task.host.hostname, port))
            if status == 0:
                print(f"{host} {task.host.hostname} is online")
                return Result(host=task.host, result=None)
            else:
                time.sleep(interval)
        except (socket.gaierror, socket.timeout, socket.error) as e:
            print(e)
        finally:
            s.close()
    raise TimedOut("Timed out waiting for: {}".format(host))
