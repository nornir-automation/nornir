from __future__ import unicode_literals

import os
import functools

from brigade.core.task import Result

import clitable

from clitable import CliTableError

from napalm.base.utils import py23_compat

from netmiko import ConnectHandler


napalm_to_netmiko_map = {
    'ios': 'cisco_ios',
    'nxos': 'cisco_nxos',
    'eos': 'arista_eos',
    'junos': 'juniper_junos',
    'iosxr': 'cisco_iosxr'
}


def get_template_dir():
    """Find and return the ntc-templates/templates dir."""
    try:
        template_dir = os.environ['NET_TEXTFSM']
        index = os.path.join(template_dir, 'index')
        if not os.path.isfile(index):
            # Assume only base ./ntc-templates specified
            template_dir = os.path.join(template_dir, 'templates')
    except KeyError:
        # Construct path ~/ntc-templates/templates
        home_dir = os.path.expanduser("~")
        template_dir = os.path.join(home_dir, 'ntc-templates', 'templates')

    index = os.path.join(template_dir, 'index')
    if not os.path.isdir(template_dir) or not os.path.isfile(index):
        msg = """
Valid ntc-templates not found, please install https://github.com/networktocode/ntc-templates
and then set the NET_TEXTFSM environment variable to point to the ./ntc-templates/templates
directory."""
        raise ValueError(msg)
    return template_dir


def get_structured_data(raw_output, platform, command):
    """Convert raw CLI output to structured data using TextFSM template."""
    template_dir = get_template_dir()
    index_file = os.path.join(template_dir, 'index')
    textfsm_obj = clitable.CliTable(index_file, template_dir)
    attrs = {'Command': command, 'Platform': platform}
    try:
        # Parse output through template
        textfsm_obj.ParseCmd(raw_output, attrs)
        return clitable_to_dict(textfsm_obj)
    except CliTableError:
        return raw_output


def clitable_to_dict(cli_table):
    """Converts TextFSM cli_table object to list of dictionaries."""
    objs = []
    for row in cli_table:
        temp_dict = {}
        for index, element in enumerate(row):
            temp_dict[cli_table.header[index].lower()] = element
        objs.append(temp_dict)
    return objs


def netmiko_get_connection(func):
    """Decorator that retrieves existing connection if it exists or establishes new connection."""
    @functools.wraps(func)
    def wrapper(task, **kwargs):
        if kwargs.get('netmiko_conn') is None:
            brigade_host = task.host
            connect_kwargs = dict(ip=kwargs.get('ip'), host=kwargs.get('host'),
                                  username=kwargs.get('username'), password=kwargs.get('password'),
                                  device_type=kwargs.get('device_type'),
                                  netmiko_dict=kwargs.get('netmiko_dict'))
            net_connect = brigade_host.get_connection("netmiko", **connect_kwargs)
            kwargs["netmiko_conn"] = net_connect
        return func(task, **kwargs)
    return wrapper


def netmiko_args(host, ip=None, netmiko_host=None, username=None, password=None, device_type=None,
                 netmiko_dict=None):
    """Process arguments coming from different sources."""

    # Both Netmiko and brigade have a host argument
    brigade_host = host
    parameters = {
        "username": username or brigade_host["brigade_username"],
        "password": password or brigade_host["brigade_password"],
    }

    if netmiko_host is None and ip is None:
        parameters["ip"] = brigade_host["brigade_ip"]
    elif ip is not None:
        parameters["ip"] = ip
    elif netmiko_host is not None:
        parameters["host"] = netmiko_host

    if netmiko_dict is not None:
        parameters.update(netmiko_dict)
    else:
        netmiko_dict = {}

    if device_type is None:
        if netmiko_dict.get("device_type") is None:
            device_type = brigade_host["nos"]
        else:
            device_type = netmiko_dict.get("device_type")

    # Convert to netmiko device_type format (if napalm format is used)
    parameters['device_type'] = napalm_to_netmiko_map.get(device_type, device_type)
    return parameters


@netmiko_get_connection
def netmiko_run(task, method, ip=None, host=None, username=None, password=None,
                device_type=None, netmiko_dict=None, cmd_args=None, cmd_kwargs=None,
                netmiko_conn=None):
    """
    Execute any Netmiko method from connection class (BaseConnection class and children).

    Arguments:
        method(str): Netmiko method to use
        ip (string, optional): defaults to ``brigade_ip``
        host (string, optional): defaults to None
        username (string, optional): defaults to ``brigade_username``
        password (string, optional): defaults to ``brigade_password``
        device_type (string, optional): Netmiko device_type to use, defaults to ``nos`` (mapped \
        through napalm_to_netmiko_map)
        netmiko_dict (dict, optional): Additional arguments to pass to Netmiko ConnectHandler, \
        defaults to None

    Returns:
        :obj:`brigade.core.task.Result`:
          * result (``dict``): dictionary with the result of the getter
    """
    # Netmiko connection automatically created by 'netmiko_get_connection' decorator (if needed)
    netmiko_method = getattr(netmiko_conn, method)
    if cmd_args is None:
        cmd_args = ()
    if cmd_kwargs is None:
        cmd_kwargs = {}
    result = netmiko_method(*cmd_args, **cmd_kwargs)
    return Result(host=task.host, result=result)


@netmiko_get_connection
def netmiko_send_command(task, ip=None, host=None, username=None, password=None,
                         device_type=None, netmiko_dict=None, use_textfsm=False,
                         cmd_args=None, cmd_kwargs=None, netmiko_conn=None):

    if cmd_args is None:
        cmd_args = ()
    elif isinstance(cmd_args, py23_compat.string_types):
        cmd_args = (cmd_args,)

    if cmd_kwargs is None:
        cmd_kwargs = {}

    if len(cmd_args) >= 1:
        command = cmd_args[0]
    else:
        command = cmd_kwargs['command_string']

    # Netmiko connection automatically created by 'netmiko_get_connection' decorator (if needed)
    result = netmiko_conn.send_command(*cmd_args, **cmd_kwargs)
    if use_textfsm:
        result = get_structured_data(result, platform=parameters['device_type'],
                                     command=command)
    return Result(host=task.host, result=result)
