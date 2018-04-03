import configparser
import logging
import os
from builtins import super

from brigade.core.inventory import Inventory

import ruamel.yaml


logger = logging.getLogger("brigade")


class AnsibleParser(object):

    def __init__(self, path):
        self.path = path
        self.hosts = {}
        self.groups = {}
        self.hostsfile = None
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
        self.groups[group] = self.map_brigade_vars(self.groups[group])

        self.parse_hosts(data.get("hosts", {}), parent=group)

        for children, children_data in data.get("children", {}).items():
            self.parse_group(children, children_data, parent=group)

    def parse(self):
        self.parse_group("defaults", self.hostsfile["all"])

    def parse_hosts(self, hosts, parent=None):
        for host, data in hosts.items():
            data = data or {}
            self.add(host, self.hosts)
            if parent:
                self.hosts[host]["groups"].append(parent)
            self.hosts[host].update(data)
            self.hosts[host].update(self.read_vars_file(host, self.path, True))
            self.hosts[host] = self.map_brigade_vars(self.hosts[host])

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
            yml = ruamel.yaml.YAML(typ='rt', pure=True)
            return yml.load(f)

    def map_brigade_vars(self, obj):
        mappings = {
            "ansible_host": "brigade_host",
            "ansible_port": "brigade_ssh_port",
            "ansible_user": "brigade_username",
            "ansible_password": "brigade_password",
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
        hostsfile = configparser.ConfigParser(
            interpolation=None, allow_no_value=True, delimiters=" "
        )
        hostsfile.read(os.path.join(self.path, "hosts"))
        data = self.normalize(hostsfile)
        data.pop("DEFAULT")
        if "all" not in data:
            self.hostsfile = {"all": {"children": data}}


class YAMLParser(AnsibleParser):

    def load_hosts_file(self):
        with open(os.path.join(self.path, "hosts"), "r") as f:
            yml = ruamel.yaml.YAML(typ='rt', pure=True)
            self.hostsfile = yml.load(f.read())


def parse(path):
    try:
        parser = INIParser(path)
    except configparser.Error:
        try:
            parser = YAMLParser(path)
        except ruamel.yaml.scanner.ScannerError:
            logger.error(
                "couldn't parse '{}' as neither a ini nor yaml file".format(path)
            )
            raise

    parser.parse()
    return parser.hosts, parser.groups


class AnsibleInventory(Inventory):
    """
    Inventory plugin that is capable of reading an ansible inventory.

    Arguments:
        path (string): Path to the directory where the host file is located
    """

    def __init__(self, path=".", **kwargs):
        host_vars, group_vars = parse(path)
        defaults = group_vars.pop("defaults")
        super().__init__(host_vars, group_vars, defaults, **kwargs)
