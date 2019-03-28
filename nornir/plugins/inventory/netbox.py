import os
from typing import Any, Dict, Optional

from nornir.core.deserializer.inventory import Inventory, HostsDict


import requests


class NBInventory(Inventory):
    def __init__(
        self,
        nb_url: Optional[str] = None,
        nb_token: Optional[str] = None,
        use_slugs: bool = True,
        flatten_custom_fields: bool = True,
        filter_parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Netbox plugin

        Arguments:
            nb_url: Netbox url, defaults to http://localhost:8080.
                You can also use env variable NB_URL
            nb_token: Netbokx token. You can also use env variable NB_TOKEN
            use_slugs: Whether to use slugs or not
            flatten_custom_fields: Whether to assign custom fields directly to the host or not
            filter_parameters: Key-value pairs to filter down hosts
        """
        filter_parameters = filter_parameters or {}

        nb_url = nb_url or os.environ.get("NB_URL", "http://localhost:8080")
        nb_token = nb_token or os.environ.get(
            "NB_TOKEN", "0123456789abcdef0123456789abcdef01234567"
        )
        headers = {"Authorization": f"Token {nb_token}"}

        def make_request(url: str) -> Dict[str, Any]:
            req = requests.get(url=url, headers=headers, params=filter_parameters)
            req.raise_for_status()

            if req.ok:
                return req.json()

        def req_all(url: str) -> Dict[str, Any]:
            req = make_request(url)
            if isinstance(req, dict) and req.get("results") is not None:
                ret = req["results"]
                first_run = True
                while req["next"]:
                    next_url = (
                        """
                        {url}
                        {'&' if url[-1] != '/' else '?'}
                        limit={req['count']}
                        &offset={len(req['results'])}
                        """
                        if first_run
                        else req["next"]
                    )
                    req = make_request(next_url)
                    first_run = False
                    ret.extend(req["results"])
                return ret
            else:
                return req

        # Create dict of hosts using 'devices' from NetBox
        nb_devices = req_all(url=f"{nb_url}/api/dcim/devices/?limit=1000")

        hosts = {}
        for d in nb_devices:
            host: HostsDict = {"data": {}}

            # Add value for IP address
            if d.get("primary_ip", {}):
                host["hostname"] = d["primary_ip"]["address"].split("/")[0]

            # Add values that do have an option for 'slug'
            if use_slugs:
                host["platform"] = d["platform"]["slug"] if d["platform"] else None
                host["data"]["site"] = d["site"]["slug"]
                host["data"]["role"] = d["device_role"]["slug"]
                host["data"]["model"] = d["device_type"]["slug"]
                host["data"]["vendor"] = d["device_type"]["manufacturer"]["slug"]

            else:
                host["platform"] = d["platform"]
                host["data"]["site"] = d["site"]["name"]
                host["data"]["role"] = d["device_role"]
                host["data"]["model"] = d["device_type"]
                host["data"]["vendor"] = d["device_type"]["manufacturer"]["name"]

            # Add values for other fields that do not have an option for 'slug'
            host["data"]["tags"] = d["tags"]
            host["data"]["rack"] = d["rack"]
            host["data"]["tenant"] = d["tenant"]
            host["data"]["status"] = d["status"]["label"]

            # Add values for device unique identification
            host["data"]["serial"] = d["serial"]
            host["data"]["asset_tag"] = d["asset_tag"]
            host["data"]["comments"] = d["comments"]

            # Add values for cluster / virtual_chassis
            host["data"]["cluster"] = d["cluster"]
            host["data"]["virtual_chassis"] = d["virtual_chassis"]
            host["data"]["vc_position"] = d["vc_position"]
            host["data"]["vc_priority"] = d["vc_priority"]

            # Add config context data
            host["data"]["local_context_data"] = d["local_context_data"]

            # Add custom fields according to 'flatten' flag
            if flatten_custom_fields:
                for cf, value in d["custom_fields"].items():
                    host["data"][cf] = value
            else:
                host["data"]["custom_fields"] = d["custom_fields"]

            # Assign temporary dict to outer dict
            hosts[d["name"]] = host

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)
