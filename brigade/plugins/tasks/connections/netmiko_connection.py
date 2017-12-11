from __future__ import unicode_literals

from brigade.plugins.tasks.networking.netmiko_tasks import netmiko_args

from netmiko import ConnectHandler


def netmiko_connection(host=None, task=None, ip=None, netmiko_host=None, username=None,
                       password=None, device_type=None, netmiko_dict=None):
    if host is None and task is None:
        raise ValueError("Must specificy either the Brigade host or the Brigade task")
    if host is None:
        host = task.host
    parameters = netmiko_args(host, ip=ip, netmiko_host=netmiko_host, username=username,
                              password=password, device_type=device_type,
                              netmiko_dict=netmiko_dict)
    host.connections["netmiko"] = ConnectHandler(**parameters)
