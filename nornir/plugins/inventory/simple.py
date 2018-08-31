import logging
import os

from nornir.core.inventory import Inventory

import ruamel.yaml


def SimpleInventory(
    host_file: str = "hosts.yaml", group_file: str = "groups.yaml"
) -> Inventory:
    yml = ruamel.yaml.YAML(typ="safe")
    with open(host_file, "r") as f:
        hosts = yml.load(f)

    if group_file:
        if os.path.exists(group_file):
            with open(group_file, "r") as f:
                groups = yml.load(f)
        else:
            logging.warning("{}: doesn't exist".format(group_file))
            groups = {}
    else:
        groups = {}
    defaults = groups.pop("defaults", {})
    return Inventory.from_dict(hosts, groups, defaults)
