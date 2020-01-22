from typing import Optional
from nornir.core.task import Result, Task


def napalm_ping(
    task: Task,
    dest: str,
    source: Optional[str] = None,
    ttl: Optional[int] = 255,
    timeout: Optional[int] = 2,
    size: Optional[int] = 100,
    count: Optional[int] = 5,
    vrf: Optional[str] = None,
) -> Result:
    """
    Executes ping on the device and returns a dictionary with the result.

    Arguments:
      dest(destination) – Host or IP Address of the destination. (type=string)
      (optional) source – Source address of echo request. (default=None) (type=string)
      (optional) ttl – Maximum number of hops. (default=255) (type=integer)
      (optional) timeout – Maximum seconds to wait after sending final packet. 
      (default=2) (type=integer)
      (optional) size – Size of request in bytes. (default=100)(type=integer)
      (optional) count – Number of ping request to send. (default=5) (type=integer)
      (optional) vrf - Name of vrf. (default=None) (type=string)

    Examples:

      Simple example::
            > nr.run(task=napalm_ping,
            >        dest='10.1.1.1')

      Passing some other optional arguments::
            > nr.run(task=napalm_ping,
            >        dest='10.1.1.1', source='10.1.1.2', size=1400, count=10)


    Returns:
       Result object with the following attributes set:
       * result (``dict``): list of dictionary with the result of the ping response.
         Output dictionary has one of following keys "success or error"


    """
    device = task.host.get_connection("napalm", task.nornir.config)
    result = device.ping(
        destination=dest, source=source, ttl=ttl, timeout=timeout, size=size, count=count, vrf=vrf
    )
    return Result(host=task.host, result=result)
