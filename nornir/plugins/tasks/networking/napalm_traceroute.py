from typing import Optional
from nornir.core.task import Result, Task


def napalm_traceroute(
    task: Task,
    dest: str,
    source: Optional[str] = None,
    ttl: Optional[int] = 255,
    timeout: Optional[int] = 2,
    vrf: Optional[str] = None,
) -> Result:

    """
    
    Executes traceroute on the device and returns a dictionary with the result.
    Arguments:
      dest(str) – Host or IP Address of the destination.
      source(str, optional) – Desired source address for trace.
      ttl(int, optional) – Max number of hops.
      timeout(int, optional) – Max seconds to wait after sending final packet.
      vrf(str, optional) - Name of vrf.
      
    Examples:
      Simple example::
            > nr.run(task=napalm_traceroute,
            >        dest='8.8.8.8')
      Passing some other optional arguments::
            > nr.run(task=napalm_traceroute,
            >        dest='8.8.8.8', source='10.1.1.2', ttl=100, timeout=1)
            
    Returns:
       Result object with the following attributes set:
       * result (``dict``): list of dictionary with the result of the trace response.
         Output dictionary has one of following keys "success or error"
         
    """
    
    device = task.host.get_connection("napalm", task.nornir.config)
    result = device.traceroute(
        destination=dest,
        source=source,
        ttl=ttl,
        timeout=timeout,
        vrf=vrf,
    )
    return Result(host=task.host, result=result)

