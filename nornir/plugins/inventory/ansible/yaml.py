from typing import cast

import ruamel.yaml

from nornir.plugins.inventory.ansible import AnsibleParser

from nornir.plugins.inventory.ansible.base import AnsibleGroupsDict

YAML = ruamel.yaml.YAML(typ="safe")


class YAMLParser(AnsibleParser):
    def load_hosts_file(self) -> None:
        with open(self.hostsfile, "r") as f:
            self.original_data = cast(AnsibleGroupsDict, YAML.load(f))
