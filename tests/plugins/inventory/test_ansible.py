import os

from nornir.plugins.inventory import ansible

import pytest

import ruamel.yaml
from ruamel.yaml.scanner import ScannerError


BASE_PATH = os.path.join(os.path.dirname(__file__), "ansible")


def save(inv_serialized, hosts_file, groups_file, defaults_file):
    yml = ruamel.yaml.YAML(typ="safe")
    yml.default_flow_style = False
    with open(hosts_file, "w+") as f:
        yml.dump(inv_serialized["hosts"], f)
    with open(groups_file, "w+") as f:
        yml.dump(inv_serialized["groups"], f)
    with open(defaults_file, "w+") as f:
        yml.dump(inv_serialized["defaults"], f)


def read(hosts_file, groups_file, defaults_file):
    yml = ruamel.yaml.YAML(typ="safe")
    with open(hosts_file, "r") as f:
        hosts = yml.load(f)
    with open(groups_file, "r") as f:
        groups = yml.load(f)
    with open(defaults_file, "r") as f:
        defaults = yml.load(f)
    return hosts, groups, defaults


class Test(object):
    @pytest.mark.parametrize("case", ["ini", "yaml", "yaml2", "yaml3"])
    def test_inventory(self, case):
        base_path = os.path.join(BASE_PATH, case)
        hosts_file = os.path.join(base_path, "expected", "hosts.yaml")
        groups_file = os.path.join(base_path, "expected", "groups.yaml")
        defaults_file = os.path.join(base_path, "expected", "defaults.yaml")

        inv = ansible.AnsibleInventory.deserialize(
            hostsfile=os.path.join(base_path, "source", "hosts")
        )
        inv_serialized = ansible.AnsibleInventory.serialize(inv).dict()

        #  save(inv_serialized, hosts_file, groups_file, defaults_file)

        expected_hosts, expected_groups, expected_defaults = read(
            hosts_file, groups_file, defaults_file
        )
        assert inv_serialized["hosts"] == expected_hosts
        assert inv_serialized["groups"] == expected_groups
        assert inv_serialized["defaults"] == expected_defaults

    def test_parse_error(self):
        base_path = os.path.join(BASE_PATH, "parse_error")
        with pytest.raises(ScannerError):
            ansible.parse(hostsfile=os.path.join(base_path, "source", "hosts"))
