try:
    import configparser as cp
except ImportError:
    import ConfigParser as cp
import logging
import os
from builtins import super

from nornir.core.inventory import Inventory

import ruamel.yaml


logger = logging.getLogger("nornir")


class AnsibleParser(object):

    def __init__(self, hostsfile):
        self.hostsfile = hostsfile
        self.path = os.path.dirname(hostsfile)
        self.hosts = {}
        self.groups = {}
        self.original_data = None
        self.load_hosts_file()

    def parse_group(self, group, data, parent=None):
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
            self.parse_group(children, children_data, parent=group)

    def parse(self):
        self.parse_group("defaults", self.original_data["all"])
        self.sort_groups()

    def parse_hosts(self, hosts, parent=None):
        for host, data in hosts.items():
            data = data or {}
            self.add(host, self.hosts)
            if parent and parent != "defaults":
                self.hosts[host]["groups"].append(parent)
            self.hosts[host].update(data)
            self.hosts[host].update(self.read_vars_file(host, self.path, True))
            self.hosts[host] = self.map_nornir_vars(self.hosts[host])

    def sort_groups(self):
        for host in self.hosts.values():
            host["groups"].sort()

        for name, group in self.groups.items():
            if name == "defaults":
                continue

            group["groups"].sort()

    def read_vars_file(self, element, path, is_host=True):
        subdir = "host_vars" if is_host else "group_vars"
        filepath = os.path.join(path, subdir, element)

        if not os.path.exists(filepath):
            logger.debug(
                "AnsibleInventory: var file doesn't exist: {}".format(filepath)
            )
            return {}

        with open(filepath, "r") as f:
            logger.debug("AnsibleInventory: reading var file: {}".format(filepath))
            yml = ruamel.yaml.YAML(typ="rt", pure=True)
            return yml.load(f)

    def map_nornir_vars(self, obj):
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

    def add(self, element, element_dict):
        if element not in element_dict:
            element_dict[element] = {"groups": []}


class INIParser(AnsibleParser):

    def normalize_content(self, content):
        result = {}

        if not content:
            return result

        for option in content.split():
            k, v = option.split("=")
            try:
                v = int(v)
            except Exception:
                pass
            result[k] = v

        return result

    def normalize(self, data):
        result = {}
        for k, v in data.items():
            meta = None
            if ":" in k:
                k, meta = k.split(":")
            if k not in result:
                result[k] = {}

            if meta not in result[k]:
                result[k][meta] = {}

            if meta == "vars":
                for data, _ in v.items():
                    result[k][meta].update(self.normalize_content(data))
            elif meta == "children":
                result[k][meta] = {k: {} for k, _ in v.items()}
            else:
                result[k]["hosts"] = {
                    host: self.normalize_content(data) for host, data in v.items()
                }
        return result

    def load_hosts_file(self):
        original_data = cp.ConfigParser(
            interpolation=None, allow_no_value=True, delimiters=" "
        )
        original_data.read(self.hostsfile)
        data = self.normalize(original_data)
        data.pop("DEFAULT")
        if "all" not in data:
            self.original_data = {"all": {"children": data}}


class YAMLParser(AnsibleParser):

    def load_hosts_file(self):
        with open(self.hostsfile, "r") as f:
            yml = ruamel.yaml.YAML(typ="rt", pure=True)
            self.original_data = yml.load(f.read())


def parse(hostsfile):
    try:
        parser = INIParser(hostsfile)
    except cp.Error:
        try:
            parser = YAMLParser(hostsfile)
        except ruamel.yaml.scanner.ScannerError:
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

    def __init__(self, hostsfile="hosts", **kwargs):
        host_vars, group_vars = parse(hostsfile)
        defaults = group_vars.pop("defaults")
        super().__init__(host_vars, group_vars, defaults, **kwargs)
