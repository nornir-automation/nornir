import os
from typing import Any, Dict, List, Optional, Union

from nornir.core.deserializer.inventory import Inventory, HostsDict

import requests


class NBInventory(Inventory):
    """
    Inventory plugin that uses `Netbox <https://github.com/netbox-community/netbox>`_ as backend.

    Note:
        Additional data provided by the Netbox devices API endpoint will be
        available through the Netbox Host data attribute.

    Environment Variables:
        * ``NB_URL``: Corresponds to nb_url argument
        * ``NB_TOKEN``: Corresponds to nb_token argument

    Arguments:
        nb_url: Netbox url (defaults to ``http://localhost:8080``)
        nb_token: Netbox API token
        ssl_verify: Enable/disable certificate validation or provide path to CA bundle file
            (defaults to True)
        flatten_custom_fields: Assign custom fields directly to the host's data attribute
            (defaults to False)
        filter_parameters: Key-value pairs that allow you to filter the Netbox inventory.
    """

    def __init__(
        self,
        nb_url: Optional[str] = None,
        nb_token: Optional[str] = None,
        use_slugs: bool = True,
        ssl_verify: Union[bool, str] = True,
        flatten_custom_fields: bool = False,
        filter_parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
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
        for dev in nb_devices:
            host: HostsDict = {"data": {}}

            # Add value for IP address
            if dev.get("primary_ip", {}):
                host["hostname"] = dev["primary_ip"]["address"].split("/")[0]

            host["platform"] = dev["platform"]

            # populate all netbox data into the hosts data attribute
            for k, v in dev.items():
                host["data"][k] = v

            if flatten_custom_fields:
                for cf, value in dev["custom_fields"].items():
                    host["data"][cf] = value
                host["data"].pop("custom_fields")

            # Assign temporary dict to outer dict
            # Netbox allows devices to be unnamed, but the Nornir model does not allow this
            # If a device is unnamed we will set the name to the id of the device in netbox
            hosts[dev.get("name") or dev.get("id")] = host

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)
