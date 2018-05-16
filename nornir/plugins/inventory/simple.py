import logging
import os
from builtins import super

from nornir.core.inventory import Inventory

import yaml


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
            nos: linux

        host2.cmh:
            site: cmh
            role: host
            groups:
                - cmh-host
            nos: linux

        switch00.cmh:
            nornir_ip: 127.0.0.1
            nornir_username: vagrant
            nornir_password: vagrant
            napalm_port: 12443
            site: cmh
            role: leaf
            groups:
                - cmh-leaf
            nos: eos

        switch01.cmh:
            nornir_ip: 127.0.0.1
            nornir_username: vagrant
            nornir_password: ""
            napalm_port: 12203
            site: cmh
            role: leaf
            groups:
                - cmh-leaf
            nos: junos

        host1.bma:
            site: bma
            role: host
            groups:
                - bma-host
            nos: linux

        host2.bma:
            site: bma
            role: host
            groups:
                - bma-host
            nos: linux

        switch00.bma:
            nornir_ip: 127.0.0.1
            nornir_username: vagrant
            nornir_password: vagrant
            napalm_port: 12443
            site: bma
            role: leaf
            groups:
                - bma-leaf
            nos: eos

        switch01.bma:
            nornir_ip: 127.0.0.1
            nornir_username: vagrant
            nornir_password: ""
            napalm_port: 12203
            site: bma
            role: leaf
            groups:
                - bma-leaf
            nos: junos

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

    def __init__(self, host_file="hosts.yaml", group_file="groups.yaml", **kwargs):
        with open(host_file, "r") as f:
            hosts = yaml.load(f.read())

        if group_file:
            if os.path.exists(group_file):
                with open(group_file, "r") as f:
                    groups = yaml.load(f.read())
            else:
                logging.warning("{}: doesn't exist".format(group_file))
                groups = {}
        else:
            groups = {}

        defaults = groups.pop("defaults", {})
        super().__init__(hosts, groups, defaults, **kwargs)
