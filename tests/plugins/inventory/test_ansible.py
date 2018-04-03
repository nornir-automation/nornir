import os

from brigade.plugins.inventory import ansible

import pytest

import yaml


BASE_PATH = os.path.join(os.path.dirname(__file__), "ansible")


def save(hosts, groups, hosts_file, groups_file):
    with open(hosts_file, "w+") as f:
        f.write(yaml.dump(hosts, default_flow_style=False))
    with open(groups_file, "w+") as f:
        f.write(yaml.dump(groups, default_flow_style=False))


def read(hosts_file, groups_file):
    with open(hosts_file, "r") as f:
        hosts = yaml.load(f.read())
    with open(groups_file, "r") as f:
        groups = yaml.load(f.read())
    return hosts, groups


class Test(object):

    @pytest.mark.parametrize("case", ["ini", "yaml"])
    def test_inventory(self, case):
        base_path = os.path.join(BASE_PATH, case)
        hosts_file = os.path.join(base_path, "expected", "hosts.yaml")
        groups_file = os.path.join(base_path, "expected", "groups.yaml")

        hosts, groups = ansible.parse(path=os.path.join(base_path, "source"))
        # save(hosts, groups, hosts_file, groups_file)

        expected_hosts, expected_groups = read(hosts_file, groups_file)
        assert hosts == expected_hosts
        assert groups == expected_groups

    def test_parse_error(self):
        base_path = os.path.join(BASE_PATH, "parse_error")
        with pytest.raises(yaml.YAMLError):
            ansible.parse(path=os.path.join(base_path, "source"))
