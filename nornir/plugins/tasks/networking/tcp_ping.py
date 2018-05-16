import socket


from nornir.core.task import Result


def tcp_ping(task, ports, timeout=2, host=None):
    """
    Tests connection to a tcp port and tries to establish a three way
    handshake. To be used for network discovery or testing.

    Arguments:
        ports (list of int): tcp port to ping
        timeout (int, optional): defaults to 0.5
        host (string, optional): defaults to ``nornir_ip``


    Returns:
        :obj:`nornir.core.task.Result`:
          * result (``dict``): Contains port numbers as keys with True/False as values
    """

    if isinstance(ports, int):
        ports = [ports]

    if isinstance(ports, list):
        if not all(isinstance(port, int) for port in ports):
            raise ValueError("Invalid value for 'ports'")

    else:
        raise ValueError("Invalid value for 'ports'")

    host = host or task.host.host

    result = {}
    for port in ports:
        s = socket.socket()
        s.settimeout(timeout)
        try:
            status = s.connect_ex((host, port))
            if status == 0:
                connection = True
            else:
                connection = False
        except (socket.gaierror, socket.timeout, socket.error):
            connection = False
        finally:
            s.close()
        result[port] = connection

    return Result(host=task.host, result=result)
