import configparser as cp
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, MutableMapping, Optional, Tuple, Union, cast

from mypy_extensions import TypedDict

from nornir.core.deserializer.inventory import (
    DefaultsDict,
    GroupsDict,
    HostsDict,
    Inventory,
    InventoryElement,
    VarsDict,
)
from nornir.core.exceptions import NornirNoValidInventoryError

import ruamel.yaml
from ruamel.yaml.composer import ComposerError
from ruamel.yaml.scanner import ScannerError


VARS_FILENAME_EXTENSIONS = ["", ".ini", ".yml", ".yaml"]


YAML = ruamel.yaml.YAML(typ="safe")

logger = logging.getLogger(__name__)


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
        self.defaults: DefaultsDict = {"data": {}}
        self.original_data: Optional[AnsibleGroupsDict] = None
        self.load_hosts_file()

    def parse_group(
        self, group: str, data: AnsibleGroupDataDict, parent: Optional[str] = None
    ) -> None:
        data = data or {}
        if group == "defaults":
            group_file = "all"
            dest_group = self.defaults
        else:
            self.add(group, self.groups)
            group_file = group
            dest_group = self.groups[group]

        if parent and parent != "defaults":
            dest_group["groups"].append(parent)

        group_data = data.get("vars", {})
        vars_file_data = self.read_vars_file(group_file, self.path, False) or {}
        self.normalize_data(dest_group, group_data, vars_file_data)
        self.map_nornir_vars(dest_group)

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

            vars_file_data = self.read_vars_file(host, self.path, True)
            self.normalize_data(self.hosts[host], data, vars_file_data)
            self.map_nornir_vars(self.hosts[host])

    def normalize_data(
        self, host: HostsDict, data: Dict[str, Any], vars_data: Dict[str, Any]
    ) -> None:
        reserved_fields = InventoryElement.__fields__.keys()
        self.map_nornir_vars(data)
        for k, v in data.items():
            if k in reserved_fields:
                host[k] = v
            else:
                host["data"][k] = v
        self.map_nornir_vars(vars_data)
        for k, v in vars_data.items():
            if k in reserved_fields:
                host[k] = v
            else:
                host["data"][k] = v

    def sort_groups(self) -> None:
        for host in self.hosts.values():
            host["groups"].sort()

        for name, group in self.groups.items():
            if name == "defaults":
                continue

            group["groups"].sort()

    @staticmethod
    def read_vars_file(element: str, path: str, is_host: bool = True) -> VarsDict:
        sub_dir = "host_vars" if is_host else "group_vars"
        vars_dir = Path(path) / sub_dir
        if vars_dir.is_dir():
            vars_file_base = vars_dir / element
            for extension in VARS_FILENAME_EXTENSIONS:
                vars_file = vars_file_base.with_suffix(
                    vars_file_base.suffix + extension
                )
                if vars_file.is_file():
                    with open(vars_file) as f:
                        logger.debug("AnsibleInventory: reading var file %r", vars_file)
                        return cast(Dict[str, Any], YAML.load(f))
            logger.debug(
                "AnsibleInventory: no vars file was found with the path %r "
                "and one of the supported extensions: %s",
                vars_file_base,
                VARS_FILENAME_EXTENSIONS,
            )
        return {}

    @staticmethod
    def map_nornir_vars(obj: VarsDict) -> None:
        mappings = {
            "ansible_host": "hostname",
            "ansible_port": "port",
            "ansible_user": "username",
            "ansible_password": "password",
        }
        for ansible_var, nornir_var in mappings.items():
            if ansible_var in obj:
                obj[nornir_var] = obj.pop(ansible_var)

    @staticmethod
    def add(element: str, element_dict: Dict[str, VarsDict]) -> None:
        if element not in element_dict:
            element_dict[element] = {"groups": [], "data": {}}

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
            self.original_data = cast(AnsibleGroupsDict, YAML.load(f))


def parse(hostsfile: str) -> Tuple[HostsDict, GroupsDict, DefaultsDict]:
    try:
        parser: AnsibleParser = INIParser(hostsfile)
    except cp.Error:
        try:
            parser = YAMLParser(hostsfile)
        except (ScannerError, ComposerError):
            logger.error("AnsibleInventory: file %r is not INI or YAML file", hostsfile)
            raise NornirNoValidInventoryError(
                f"AnsibleInventory: no valid inventory source(s) to parse. Tried: {hostsfile}"
            )

    parser.parse()

    return parser.hosts, parser.groups, parser.defaults


class AnsibleInventory(Inventory):
    def __init__(self, hostsfile: str = "hosts", *args: Any, **kwargs: Any) -> None:
        """
        Ansible Inventory plugin supporting ini, yaml, and dynamic inventory sources.

        Arguments:
            hostsfile: Path to valid Ansible inventory

        """
        host_vars, group_vars, defaults = parse(hostsfile)
        super().__init__(
            hosts=host_vars, groups=group_vars, defaults=defaults, *args, **kwargs
        )
