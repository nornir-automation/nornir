import os
from typing import Any, Dict, List, Optional, Union

from nornir.core.deserializer.inventory import Inventory, HostsDict


import requests


class NBInventory(Inventory):
    def __init__(
        self,
        nb_url: Optional[str] = None,
        nb_token: Optional[str] = None,
        use_slugs: bool = True,
        ssl_verify: Union[bool, str] = True,
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
            ssl_verify: Enable/disable certificate validation or provide path to CA bundle file
            flatten_custom_fields: Whether to assign custom fields directly to the host or not
            filter_parameters: Key-value pairs to filter down hosts
        """
        filter_parameters = filter_parameters or {}
        nb_url = nb_url or os.environ.get("NB_URL", "http://localhost:8080")
        nb_token = nb_token or os.environ.get(
            "NB_TOKEN", "0123456789abcdef0123456789abcdef01234567"
        )

        session = requests.Session()
        session.headers.update({"Authorization": f"Token {nb_token}"})
        session.verify = ssl_verify

        # Fetch all devices from Netbox
        # Since the api uses pagination we have to fetch until no next is provided

        url = f"{nb_url}/api/dcim/devices/?limit=0"
        nb_devices: List[Dict[str, Any]] = []

        while url:
            r = session.get(url, params=filter_parameters)

            if not r.status_code == 200:
                raise ValueError(f"Failed to get devices from Netbox instance {nb_url}")

            resp = r.json()
            nb_devices.extend(resp.get("results"))

            url = resp.get("next")

        hosts = {}
        for d in nb_devices:
            host: HostsDict = {"data": {}}

            # Add value for IP address
            if d.get("primary_ip", {}):
                host["hostname"] = d["primary_ip"]["address"].split("/")[0]

            # Add values that don't have an option for 'slug'
            host["data"]["serial"] = d["serial"]
            host["data"]["vendor"] = d["device_type"]["manufacturer"]["name"]
            host["data"]["asset_tag"] = d["asset_tag"]

            if flatten_custom_fields:
                for cf, value in d["custom_fields"].items():
                    host["data"][cf] = value
            else:
                host["data"]["custom_fields"] = d["custom_fields"]

            # Add values that do have an option for 'slug'
            if use_slugs:
                host["data"]["site"] = d["site"]["slug"]
                host["data"]["role"] = d["device_role"]["slug"]
                host["data"]["model"] = d["device_type"]["slug"]

                # Attempt to add 'platform' based of value in 'slug'
                host["platform"] = d["platform"]["slug"] if d["platform"] else None

            else:
                host["data"]["site"] = d["site"]["name"]
                host["data"]["role"] = d["device_role"]
                host["data"]["model"] = d["device_type"]
                host["platform"] = d["platform"]

            # Assign temporary dict to outer dict
            hosts[d["name"]] = host

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)
