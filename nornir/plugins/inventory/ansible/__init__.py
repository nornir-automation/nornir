import configparser as cp
import logging
from pathlib import Path
from typing import Any, MutableMapping, Tuple


from nornir.core.deserializer.inventory import (
    DefaultsDict,
    GroupsDict,
    HostsDict,
    Inventory,
)
from nornir.core.exceptions import NornirNoValidInventoryError

from ruamel.yaml.composer import ComposerError
from ruamel.yaml.scanner import ScannerError

from nornir.plugins.inventory.ansible.base import AnsibleParser
from nornir.plugins.inventory.ansible.ini import INIParser
from nornir.plugins.inventory.ansible.yaml import YAMLParser
from nornir.plugins.inventory.ansible.script import ScriptParser


VARS_FILENAME_EXTENSIONS = ["", ".ini", ".py", ".yml", ".yaml"]

logger = logging.getLogger(__name__)


def parse(
    hostsfile: str, inventory: str = "", hash_behavior: str = "replace"
) -> Tuple[HostsDict, GroupsDict, DefaultsDict]:
    sources = []

    # add hostsfile to to sources to preserve existing functionality
    if Path(hostsfile).expanduser().is_file():
        sources.append(hostsfile)

    if inventory:
        if Path(inventory).expanduser().is_dir():
            files = Path(inventory).glob("*")
            sources.extend([f for f in files if f.suffix in VARS_FILENAME_EXTENSIONS])
        elif Path(inventory).expanduser().is_file():
            sources.append(inventory)

    valid_sources = []
    for source in sources:
        try:
            parser: AnsibleParser = INIParser(source)
            valid_sources.append(parser)
            continue
        except cp.Error:
            logger.error(
                "AnsibleInventory: file %r is not INI file, moving to next parser...",
                source,
            )
        try:
            parser = YAMLParser(source)
            valid_sources.append(parser)
            continue
        except (ScannerError, ComposerError):
            logger.error(
                "AnsibleInventory: file %r is not YAML file, moving to next parser...",
                source,
            )
        try:
            parser: AnsibleParser = ScriptParser(source)
            valid_sources.append(parser)
            continue
        except Exception as e:
            logger.error(
                "AnsibleInventory: file %r is not Python file, no more parsers to try...",
                source,
            )

    if not valid_sources:
        raise NornirNoValidInventoryError(
            "AnsibleInventory: no valid inventory source(s) to parse. Tried: %r",
            sources,
        )

    hosts = {}
    groups = {}
    defaults = {}

    for source in valid_sources:
        source.parse()
        hosts = combine_vars(hosts, source.hosts, hash_behavior)
        groups = combine_vars(groups, source.groups, hash_behavior)
        defaults = combine_vars(defaults, source.defaults, hash_behavior)

    return hosts, groups, defaults


def combine_vars(a, b, hash_behavior):
    """
    stolen from ansible
    """
    if hash_behavior == "merge":
        return merge_hash(a, b)
    return replace_hash(a, b)


def merge_hash(a, b):
    """
    stolen from ansible
    """
    if a == {} or a == b:
        return b.copy()
    result = a.copy()
    for k, v in b.items():
        if (
            k in result
            and isinstance(result[k], MutableMapping)
            and isinstance(v, MutableMapping)
        ):
            result[k] = merge_hash(result[k], v)
        else:
            result[k] = v
    return result


def replace_hash(a, b):
    result = a.copy()
    result.update(b)
    return result


class AnsibleInventory(Inventory):
    def __init__(
        self,
        hostsfile: str = "hosts",
        inventory: str = "",
        hash_behavior: str = "merge",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        host_vars, group_vars, defaults = parse(hostsfile, inventory, hash_behavior)
        super().__init__(
            hosts=host_vars, groups=group_vars, defaults=defaults, *args, **kwargs
        )
