import logging
import os
from typing import Any

from nornir.core.inventory import Inventory, GroupsDict, HostsDict, VarsDict

import ruamel.yaml


class SimpleInventory(Inventory):
    """
    This is a very simple file based inventory. Basically you need two yaml files. One
    for your host information and another one for your group information.

    * host file::

        ---
        host1.cmh:
            site: cmh
            role: host
            groups:
                - cmh-host
            platform: linux

        host2.cmh:
            site: cmh
            role: host
            groups:
                - cmh-host
            platform: linux

        switch00.cmh:
            hostname: 127.0.0.1
            username: vagrant
            password: vagrant
            napalm_port: 12443
            site: cmh
            role: leaf
            groups:
                - cmh-leaf
            platform: eos

        switch01.cmh:
            hostname: 127.0.0.1
            username: vagrant
            password: ""
            napalm_port: 12203
            site: cmh
            role: leaf
            groups:
                - cmh-leaf
            platform: juplatform

        host1.bma:
            site: bma
            role: host
            groups:
                - bma-host
            platform: linux

        host2.bma:
            site: bma
            role: host
            groups:
                - bma-host
            platform: linux

        switch00.bma:
            hostname: 127.0.0.1
            username: vagrant
            password: vagrant
            napalm_port: 12443
            site: bma
            role: leaf
            groups:
                - bma-leaf
            platform: eos

        switch01.bma:
            hostname: 127.0.0.1
            username: vagrant
            password: ""
            napalm_port: 12203
            site: bma
            role: leaf
            groups:
                - bma-leaf
            platform: juplatform

    * group file::

        ---
        defaults:
            domain: acme.com

        bma-leaf:
            groups:
                - bma

        bma-host:
            groups:
                - bma

        bma:
            domain: bma.acme.com

        cmh-leaf:
            groups:
                - cmh

        cmh-host:
            groups:
                - cmh

        cmh:
            domain: cmh.acme.com
    """

    def __init__(
        self,
        host_file: str = "hosts.yaml",
        group_file: str = "groups.yaml",
        **kwargs: Any
    ) -> None:
        yml = ruamel.yaml.YAML(typ="safe")
        with open(host_file, "r") as f:
            hosts: HostsDict = yml.load(f)

        if group_file:
            if os.path.exists(group_file):
                with open(group_file, "r") as f:
                    groups: GroupsDict = yml.load(f)
            else:
                logging.warning("{}: doesn't exist".format(group_file))
                groups = {}
        else:
            groups = {}

        defaults: VarsDict = groups.pop("defaults", {})
        super().__init__(hosts, groups, defaults, **kwargs)
