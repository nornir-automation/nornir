try:
    import configparser as cp
except ImportError:
    # https://github.com/python/mypy/issues/1153
    import ConfigParser as cp  # type: ignore
import logging
import os
from collections import defaultdict
from typing import Dict, Any, Tuple, Optional, cast, Union, MutableMapping, DefaultDict
from mypy_extensions import TypedDict

import ruamel.yaml
from ruamel.yaml.scanner import ScannerError
from ruamel.yaml.composer import ComposerError

from nornir.core.inventory import Inventory, VarsDict, GroupsDict, HostsDict


logger = logging.getLogger("nornir")


AnsibleHostsDict = Dict[str, Optional[VarsDict]]

AnsibleGroupDataDict = TypedDict(
    "AnsibleGroupDataDict",
    {"children": Dict[str, Any], "vars": VarsDict, "hosts": AnsibleHostsDict},
    total=False,
)  # bug: https://github.com/python/mypy/issues/5357

AnsibleGroupsDict = Dict[str, AnsibleGroupDataDict]


class AnsibleParser(object):
    def __init__(self, hostsfile: str) -> None:
        self.hostsfile = hostsfile
        self.path = os.path.dirname(hostsfile)
        self.hosts: HostsDict = {}
        self.groups: GroupsDict = {}
        self.original_data: Optional[AnsibleGroupsDict] = None
        self.load_hosts_file()

    def parse_group(
        self, group: str, data: AnsibleGroupDataDict, parent: Optional[str] = None
    ) -> None:
        data = data or {}
        if group == "defaults":
            self.groups[group] = {}
            group_file = "all"
        else:
            self.add(group, self.groups)
            group_file = group

        if parent and parent != "defaults":
            self.groups[group]["groups"].append(parent)

        self.groups[group].update(data.get("vars", {}))
        self.groups[group].update(self.read_vars_file(group_file, self.path, False))
        self.groups[group] = self.map_nornir_vars(self.groups[group])

        self.parse_hosts(data.get("hosts", {}), parent=group)

        for children, children_data in data.get("children", {}).items():
            self.parse_group(
                children, cast(AnsibleGroupDataDict, children_data), parent=group
            )

    def parse(self) -> None:
        if self.original_data is not None:
            self.parse_group("defaults", self.original_data["all"])
        self.sort_groups()

    def parse_hosts(
        self, hosts: AnsibleHostsDict, parent: Optional[str] = None
    ) -> None:
        for host, data in hosts.items():
            data = data or {}
            self.add(host, self.hosts)
            if parent and parent != "defaults":
                self.hosts[host]["groups"].append(parent)
            self.hosts[host].update(data)
            self.hosts[host].update(self.read_vars_file(host, self.path, True))
            self.hosts[host] = self.map_nornir_vars(self.hosts[host])

    def sort_groups(self) -> None:
        for host in self.hosts.values():
            host["groups"].sort()

        for name, group in self.groups.items():
            if name == "defaults":
                continue

            group["groups"].sort()

    @staticmethod
    def read_vars_file(element: str, path: str, is_host: bool = True) -> VarsDict:
        subdir = "host_vars" if is_host else "group_vars"
        filepath = os.path.join(path, subdir, element)

        if not os.path.exists(filepath):
            logger.debug(
                "AnsibleInventory: var file doesn't exist: {}".format(filepath)
            )
            return {}

        with open(filepath, "r") as f:
            logger.debug("AnsibleInventory: reading var file: {}".format(filepath))
            yml = ruamel.yaml.YAML()
            return yml.load(f)

    @staticmethod
    def map_nornir_vars(obj: VarsDict):
        mappings = {
            "ansible_host": "nornir_host",
            "ansible_port": "nornir_ssh_port",
            "ansible_user": "nornir_username",
            "ansible_password": "nornir_password",
        }
        result = {}
        for k, v in obj.items():
            if k in mappings:
                result[mappings[k]] = v
            else:
                result[k] = v
        return result

    @staticmethod
    def add(element: str, element_dict: Dict[str, VarsDict]) -> None:
        if element not in element_dict:
            element_dict[element] = {"groups": []}

    def load_hosts_file(self) -> None:
        raise NotImplementedError


class INIParser(AnsibleParser):
    @staticmethod
    def normalize_value(value: str) -> Union[str, int]:
        try:
            return int(value)

        except (ValueError, TypeError):
            return value

    @staticmethod
    def normalize_content(content: str) -> VarsDict:
        result: VarsDict = {}

        if not content:
            return result

        for option in content.split():
            key, value = option.split("=")
            result[key] = INIParser.normalize_value(value)
        return result

    @staticmethod
    def process_meta(
        meta: Optional[str], section: MutableMapping[str, str]
    ) -> Dict[str, Any]:
        if meta == "vars":
            return {
                key: INIParser.normalize_value(value) for key, value in section.items()
            }

        elif meta == "children":
            return {group_name: {} for group_name in section}

        else:
            raise ValueError(f"Unknown tag {meta}")

    def normalize(self, data: cp.ConfigParser) -> Dict[str, AnsibleGroupDataDict]:
        groups: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
        # Dict[str, AnsibleGroupDataDict] does not work because of
        # https://github.com/python/mypy/issues/5359
        result: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {
            "all": {"children": groups}
        }

        for section_name, section in data.items():

            if section_name == "DEFAULT":
                continue

            if ":" in section_name:
                group_name, meta = section_name.split(":")
                subsection = self.process_meta(meta, section)
                if group_name == "all":
                    result["all"][meta] = subsection
                else:
                    groups[group_name][meta] = subsection
            else:
                groups[section_name]["hosts"] = {
                    host: self.normalize_content(host_vars)
                    for host, host_vars in section.items()
                }
        return cast(AnsibleGroupsDict, result)

    def load_hosts_file(self) -> None:
        original_data = cp.ConfigParser(
            interpolation=None, allow_no_value=True, delimiters=" ="
        )
        original_data.read(self.hostsfile)
        self.original_data = self.normalize(original_data)


class YAMLParser(AnsibleParser):
    def load_hosts_file(self) -> None:
        with open(self.hostsfile, "r") as f:
            yml = ruamel.yaml.YAML()
            self.original_data = cast(AnsibleGroupsDict, yml.load(f))


def parse(hostsfile: str) -> Tuple[HostsDict, GroupsDict]:
    try:
        parser: AnsibleParser = INIParser(hostsfile)
    except cp.Error:
        try:
            parser = YAMLParser(hostsfile)
        except (ScannerError, ComposerError):
            logger.error(
                "couldn't parse '{}' as neither a ini nor yaml file".format(hostsfile)
            )
            raise

    parser.parse()

    return parser.hosts, parser.groups


class AnsibleInventory(Inventory):
    """
    Inventory plugin that is capable of reading an ansible inventory.

    Arguments:
        hostsfile (string): Ansible inventory file to load
    """

    def __init__(self, hostsfile: str = "hosts", **kwargs: Any) -> None:
        host_vars, group_vars = parse(hostsfile)
        defaults = group_vars.pop("defaults")
        super().__init__(host_vars, group_vars, defaults, **kwargs)
