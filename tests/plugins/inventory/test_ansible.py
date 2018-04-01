import os

from brigade.plugins.inventory import ansible

import yaml


BASE_PATH = os.path.join(os.path.dirname(__file__), "ansible")
HOSTS_FILE = os.path.join(BASE_PATH, "expected", "hosts.yaml")
GROUPS_FILE = os.path.join(BASE_PATH, "expected", "groups.yaml")


def save(hosts, groups):
    with open(HOSTS_FILE, "w+") as f:
        f.write(yaml.dump(hosts, default_flow_style=False))
    with open(GROUPS_FILE, "w+") as f:
        f.write(yaml.dump(groups, default_flow_style=False))


def read():
    with open(HOSTS_FILE, "r") as f:
        hosts = yaml.load(f.read())
    with open(GROUPS_FILE, "r") as f:
        groups = yaml.load(f.read())
    return hosts, groups


class Test(object):

    def test_inventory(self):
        hosts, groups = ansible.parse(path=os.path.join(BASE_PATH, "source"))
        # save(hosts, groups)
        expected_hosts, expected_groups = read()
        assert hosts == expected_hosts
        assert groups == expected_groups
