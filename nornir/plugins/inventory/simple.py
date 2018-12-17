import logging
import os

from nornir.core.deserializer.inventory import GroupsDict, Inventory, VarsDict

import ruamel.yaml


class SimpleInventory(Inventory):
    def __init__(
        self,
        host_file: str = "hosts.yaml",
        group_file: str = "groups.yaml",
        defaults_file: str = "defaults.yaml",
        *args,
        **kwargs
    ) -> None:
        yml = ruamel.yaml.YAML(typ="safe")
        with open(host_file, "r") as f:
            hosts = yml.load(f)

        groups: GroupsDict = {}
        if group_file:
            if os.path.exists(group_file):
                with open(group_file, "r") as f:
                    groups = yml.load(f) or {}
            else:
                logging.debug("{}: doesn't exist".format(group_file))
                groups = {}

        defaults: VarsDict = {}
        if defaults_file:
            if os.path.exists(defaults_file):
                with open(defaults_file, "r") as f:
                    defaults = yml.load(f) or {}
            else:
                logging.debug("{}: doesn't exist".format(defaults_file))
                defaults = {}
        super().__init__(hosts=hosts, groups=groups, defaults=defaults, *args, **kwargs)
