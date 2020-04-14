import os
from nornir.core import Nornir
from nornir.core.inventory import (
    Inventory,
    Host,
    Hosts,
    Group,
    Groups,
    Defaults,
    ParentGroups,
    ConnectionOptions,
)
from nornir.core.state import GlobalState

import ruamel.yaml
import pytest


global_data = GlobalState(dry_run=True)


def inventory_from_yaml():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    yml = ruamel.yaml.YAML(typ="safe")

    def get_connection_options(data):
        cp = {}
        for cn, c in data.items():
            cp[cn] = ConnectionOptions(
                hostname=c.get("hostname"),
                port=c.get("port"),
                username=c.get("username"),
                password=c.get("password"),
                platform=c.get("platform"),
                extras=c.get("extras"),
            )
        return cp

    def get_defaults():
        defaults_file = f"{dir_path}/inventory_data/defaults.yaml"
        with open(defaults_file, "r") as f:
            defaults_dict = yml.load(f)

            defaults = Defaults(
                hostname=defaults_dict.get("hostname"),
                port=defaults_dict.get("port"),
                username=defaults_dict.get("username"),
                password=defaults_dict.get("password"),
                platform=defaults_dict.get("platform"),
                data=defaults_dict.get("data"),
                connection_options=get_connection_options(
                    defaults_dict.get("connection_options", {})
                ),
            )

        return defaults

    host_file = f"{dir_path}/inventory_data/hosts.yaml"
    group_file = f"{dir_path}/inventory_data/groups.yaml"

    defaults = get_defaults()

    hosts = Hosts()
    with open(host_file, "r") as f:
        hosts_dict = yml.load(f)

    for n, h in hosts_dict.items():
        hosts[n] = Host(
            name=n,
            hostname=h.get("hostname"),
            port=h.get("port"),
            username=h.get("username"),
            password=h.get("password"),
            platform=h.get("platform"),
            data=h.get("data"),
            groups=h.get(
                "groups"
            ),  # this is a hack, we will convert it later to the correct type
            defaults=defaults,
            connection_options=get_connection_options(h.get("connection_options", {})),
        )

    groups = Groups()
    with open(group_file, "r") as f:
        groups_dict = yml.load(f)
    for n, g in groups_dict.items():
        groups[n] = Group(
            name=n,
            hostname=g.get("hostname"),
            port=g.get("port"),
            username=g.get("username"),
            password=g.get("password"),
            platform=g.get("platform"),
            data=g.get("data"),
            groups=g.get(
                "groups"
            ),  # this is a hack, we will convert it later to the correct type
            defaults=defaults,
            connection_options=get_connection_options(g.get("connection_options", {})),
        )

    for h in hosts.values():
        h.groups = ParentGroups([groups[g] for g in h.groups])

    for g in groups.values():
        g.groups = ParentGroups([groups[g] for g in g.groups])

    return Inventory(hosts=hosts, groups=groups, defaults=defaults)


@pytest.fixture(scope="session", autouse=True)
def inv(request):
    return inventory_from_yaml()


@pytest.fixture(scope="session", autouse=True)
def nornir(request):
    """Initializes nornir"""
    nr = Nornir(inventory=inventory_from_yaml(), data=global_data)
    return nr


@pytest.fixture(scope="function", autouse=True)
def reset_data():
    global_data.dry_run = True
    global_data.reset_failed_hosts()
