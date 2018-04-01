import configparser
import logging
import os
from builtins import super

from brigade.core.inventory import Inventory

import yaml


logger = logging.getLogger("brigade")


def read_hostdata_from_hostfile(host_data):
    if host_data:
        return {k: v for k, v in [option.split("=") for option in host_data.split()]}
    else:
        return {}


def read_vars_file(element, path, is_host=True):
    subdir = "host_vars" if is_host else "group_vars"
    filepath = os.path.join(path, subdir, element)

    if not os.path.exists(filepath):
        logger.debug("AnsibleInventory: var file doesn't exist: {}".format(filepath))
        return {}

    with open(filepath, "r") as f:
        logger.debug("AnsibleInventory: reading var file: {}".format(filepath))
        return yaml.load(f)


def map_brigade_vars(obj):
    mappings = {
        "ansible_host": "brigade_host",
        "ansible_port": "brigade_ssh_port",
        "ansible_user": "brigade_username",
        "ansible_password": "brigade_password",
    }
    result = {}
    for k, v in obj.items():
        if k in mappings:
            result[mappings[k]] = v
        else:
            result[k] = v
    return result


def parse(path):
    hostfile = configparser.ConfigParser(
        interpolation=None, allow_no_value=True, delimiters=" "
    )
    hostfile.read(os.path.join(path, "hosts"))

    host_vars = {}
    group_vars = {}

    for group, group_data in hostfile.items():
        meta = None
        if ":" in group:
            group, meta = group.split(":")

        if group not in group_vars:
            group_vars[group] = {"groups": []}

        group_vars[group].update(read_vars_file(group, path, False))

        if meta == "vars":
            for data, _ in group_data.items():
                group_vars[group].update(read_hostdata_from_hostfile(data))
        elif meta == "children":
            for children, _ in group_data.items():
                group_vars[children]["groups"].append(group)
        else:
            for host, host_data in group_data.items():
                if host not in host_vars:
                    host_vars[host] = {"groups": []}

                host_vars[host]["groups"].append(group)

                host_vars[host].update(read_hostdata_from_hostfile(host_data))
                host_vars[host].update(read_vars_file(host, path, True))

                host_vars[host] = map_brigade_vars(host_vars[host])
        group_vars[group] = map_brigade_vars(group_vars[group])

    group_vars.pop("DEFAULT")
    group_vars["defaults"] = read_vars_file("all", path, False)
    return host_vars, group_vars


class AnsibleInventory(Inventory):
    """
    Inventory plugin that is capable of reading an ansible inventory.

    Arguments:
        path (string): Path to the directory where the host file is located
    """
    def __init__(self, path=".", **kwargs):
        host_vars, group_vars = parse(path)
        defaults = group_vars.pop("defaults")
        super().__init__(host_vars, group_vars, defaults, **kwargs)
