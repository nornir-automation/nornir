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
        use_platform_args: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Netbox plugin

        Arguments:
            nb_url: NetBox url, defaults to http://localhost:8080.
                You can also use env variable NB_URL
            nb_token: NetbBox token. You can also use env variable NB_TOKEN
            use_slugs: Whether to use slugs or not
            ssl_verify: Enable/disable certificate validation or provide path to CA bundle file
            flatten_custom_fields: Whether to assign custom fields directly to the host or not
            filter_parameters: Key-value pairs to filter down hosts
            use_platform_args: Whether to import NetBox NAPALM platform options as
                connection options for the NAPALM driver
        """
        filter_parameters = filter_parameters or {}
        nb_url = nb_url or os.environ.get("NB_URL", "http://localhost:8080")
        nb_token = nb_token or os.environ.get(
            "NB_TOKEN", "0123456789abcdef0123456789abcdef01234567"
        )

        session = requests.Session()
        session.headers.update({"Authorization": f"Token {nb_token}"})
        session.verify = ssl_verify

        # Fetch all platforms from Netbox
        if use_platform_args:
            nb_platforms = self._get_resources(
                session, f"{nb_url}/api/dcim/platforms/?limit=0", {}
            )
            platform_field = "slug" if use_slugs else "name"
            napalm_args = {p[platform_field]: p["napalm_args"] for p in nb_platforms}

        # Fetch all devices from Netbox
        nb_devices = self._get_resources(
            session, f"{nb_url}/api/dcim/devices/?limit=0", filter_parameters
        )

        hosts = {}
        for d in nb_devices:
            host: HostsDict = {"data": {}, "connection_options": {}}

            # Add value for IP address
            if d.get("primary_ip", {}):
                host["hostname"] = d["primary_ip"]["address"].split("/")[0]
            else:
                # Set to the hostname in NetBox if not a primary IP, expect DNS will be in place
                if d.get("name") is not None:
                    host["hostname"] = d["name"]

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
                host["platform"] = (
                    d["platform"]["slug"]
                    if isinstance(d["platform"], dict)
                    else d["platform"]
                )

            else:
                host["data"]["site"] = d["site"]["name"]
                host["data"]["role"] = d["device_role"]
                host["data"]["model"] = d["device_type"]
                host["platform"] = (
                    d["platform"]["name"]
                    if isinstance(d["platform"], dict)
                    else d["platform"]
                )

            if use_platform_args:
                # Add NAPALM connection options if they exist for the host platform
                if napalm_args.get(host["platform"]):
                    if os.environ.get("NB_PLATFORM_AS_CONN_OPTS", "0") == "1":
                        # Abuse the platform NAPALM arguments field for use as
                        # connection_options for any connection driver
                        host["connection_options"] = napalm_args[host["platform"]]
                    else:
                        # Use the platform NAPALM arguments as intended by NetBox
                        host["connection_options"]["napalm"] = {
                            "extras": {"optional_args": napalm_args[host["platform"]]}
                        }

            # Assign temporary dict to outer dict
            # Netbox allows devices to be unnamed, but the Nornir model does not allow this
            # If a device is unnamed we will set the name to the id of the device in netbox
            hosts[d.get("name") or d.get("id")] = host

        # Pass the data back to the parent class
        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)

    def _get_resources(
        self,
        session: requests.sessions.Session,
        url: str,
        parameters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get data from Netbox API"""
        nb_result: List[Dict[str, Any]] = []

        # Since the api uses pagination we have to fetch until no next is provided
        while url:
            r = session.get(url, params=parameters)

            if not r.status_code == 200:
                raise ValueError(
                    f"Failed to get valid response from Netbox instance {url}"
                )

            resp = r.json()
            nb_result.extend(resp.get("results"))

            url = resp.get("next")

        return nb_result
