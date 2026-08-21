import pathlib
from typing import Any, TypeVar

import pytest
import ruamel.yaml

from nornir.core import Nornir
from nornir.core.inventory import (
    ConnectionOptions,
    Defaults,
    Group,
    Groups,
    Host,
    Hosts,
    Inventory,
    ParentGroups,
)
from nornir.core.state import GlobalState
from nornir.core.task import AggregatedResult, Task

ElementType = TypeVar("ElementType", bound=Group | Host)

global_data = GlobalState(dry_run=True)


def inventory_from_yaml() -> Inventory:
    data_path = pathlib.Path(__file__).resolve().parent / "inventory_data"
    yml = ruamel.yaml.YAML(typ="safe")

    def get_connection_options(data: dict[str, Any]) -> dict[str, ConnectionOptions]:
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

    def get_defaults() -> Defaults:
        defaults_file = data_path / "defaults.yaml"
        with defaults_file.open("r") as f:
            defaults_dict = yml.load(f)

            return Defaults(
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

    def get_inventory_element(
        typ: type[ElementType], data: dict[str, Any], name: str, defaults: Defaults | None
    ) -> ElementType:
        return typ(
            name=name,
            hostname=data.get("hostname"),
            port=data.get("port"),
            username=data.get("username"),
            password=data.get("password"),
            platform=data.get("platform"),
            data=data.get("data"),
            groups=data.get(
                "groups"
            ),  # this is a hack, we will convert it later to the correct type
            defaults=defaults,
            connection_options=get_connection_options(data.get("connection_options", {})),
        )

    host_file = data_path / "hosts.yaml"
    group_file = data_path / "groups.yaml"

    defaults = get_defaults()

    hosts = Hosts()
    with host_file.open("r") as f:
        hosts_dict = yml.load(f)

    for n, h in hosts_dict.items():
        hosts[n] = get_inventory_element(Host, h, n, defaults)

    groups = Groups()
    with group_file.open("r") as f:
        groups_dict = yml.load(f)

    for n, g in groups_dict.items():
        groups[n] = get_inventory_element(Group, g, n, defaults)

    for h in hosts.values():
        h.groups = ParentGroups([groups[g] for g in h.groups])

    for g in groups.values():
        g.groups = ParentGroups([groups[g] for g in g.groups])

    return Inventory(hosts=hosts, groups=groups, defaults=defaults)


class SerialRunner:
    """Runner that executes the task over each host sequentially without parallelization."""

    def __init__(self) -> None:
        pass

    def run(self, task: Task, hosts: list[Host]) -> AggregatedResult:
        result = AggregatedResult(task.name)
        for host in hosts:
            result[host.name] = task.copy().start(host)
        return result


@pytest.fixture(scope="session", autouse=True)
def inv() -> Inventory:
    return inventory_from_yaml()


@pytest.fixture(scope="session", autouse=True)
def nornir() -> Nornir:
    """Initialize nornir.

    Returns:
        A Nornir object using the test inventory and a serial runner.

    """
    return Nornir(inventory=inventory_from_yaml(), runner=SerialRunner(), data=global_data)


@pytest.fixture(autouse=True)
def reset_data() -> None:
    global_data.dry_run = True
    global_data.reset_failed_hosts()
