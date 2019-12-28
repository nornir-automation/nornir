from collections import defaultdict
import json
import os
import subprocess
from typing import Any, DefaultDict, Dict

from nornir.plugins.inventory.ansible import AnsibleParser


class ScriptParser(AnsibleParser):
    def verify_file(self):
        shebang_present = False
        with open(self.hostsfile, "rb") as inv_file:
            initial_chars = inv_file.read(2)
            if initial_chars.startswith(b"#!"):
                shebang_present = True

        if not os.access(self.hostsfile, os.X_OK) and not shebang_present:
            raise OSError("Script not executable")

    def load_hosts_file(self) -> None:
        self.verify_file()
        cmd = [self.hostsfile, "--list"]

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            std_out, std_err = proc.communicate()
        except OSError as e:
            raise e

        if proc.returncode != 0:
            raise OSError(
                "AnsibleInventory: %r exited with non-zero return code", self.hostsfile
            )

        try:
            processed = json.loads(std_out.decode())
        except Exception as e:
            raise e

        # self.original_data = processed
        self.original_data = self.normalize(processed)

    def normalize(self, data):
        groups: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
        # Dict[str, AnsibleGroupDataDict] does not work because of
        # https://github.com/python/mypy/issues/5359
        result: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {
            "all": {"children": groups}
        }

        hostvars = data.get("_meta", {}).get("hostvars", None)

        for group, gdata in data.items():
            if group == "all" and "vars" in gdata.keys():
                result["all"]["vars"] = gdata["vars"]
            if "vars" in gdata.keys():
                groups[group]["vars"] = gdata["vars"]
            if "hosts" in gdata.keys():
                if isinstance(gdata["hosts"], list):
                    groups[group]["hosts"] = {}
                    for host in gdata["hosts"]:
                        groups[group]["hosts"][host] = hostvars.get(host, None)
        return result
