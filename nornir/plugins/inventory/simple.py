import logging
import os
from typing import Any, Optional

from nornir.core.deserializer.inventory import (
    HostsDict,
    GroupsDict,
    Inventory,
    VarsDict,
)

import ruamel.yaml

logger = logging.getLogger(__name__)


class SimpleInventory(Inventory):
    def __init__(
        self,
        host_file: str = "hosts.yaml",
        group_file: str = "groups.yaml",
        defaults_file: str = "defaults.yaml",
        hosts: Optional[HostsDict] = None,
        groups: Optional[GroupsDict] = None,
        defaults: Optional[VarsDict] = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        yml = ruamel.yaml.YAML(typ="safe")
        if hosts is None:
            with open(os.path.expanduser(host_file), "r") as f:
                hosts = yml.load(f)

        if groups is None:
            groups = {}
            if group_file:
                group_file = os.path.expanduser(group_file)
                if os.path.exists(group_file):
                    with open(group_file, "r") as f:
                        groups = yml.load(f) or {}
                else:
                    logger.debug("File %r was not found", group_file)
                    groups = {}

        if defaults is None:
            defaults = {}
            if defaults_file:
                defaults_file = os.path.expanduser(defaults_file)
                if os.path.exists(defaults_file):
                    with open(defaults_file, "r") as f:
                        defaults = yml.load(f) or {}
                else:
                    logger.debug("File %r was not found", defaults_file)
                    defaults = {}
        super().__init__(hosts=hosts, groups=groups, defaults=defaults, *args, **kwargs)
