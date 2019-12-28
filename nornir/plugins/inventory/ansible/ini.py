from collections import defaultdict
import configparser as cp
from typing import Any, DefaultDict, Dict, MutableMapping, Optional, Union, cast

from nornir.core.deserializer.inventory import VarsDict
from nornir.plugins.inventory.ansible import AnsibleParser
from nornir.plugins.inventory.ansible.base import (
    AnsibleGroupDataDict,
    AnsibleGroupsDict,
)


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
