import os
from builtins import super

from nornir.core.inventory import Inventory

import requests


class NBInventory(Inventory):
    def __init__(
        self,
        nb_url=None,
        nb_token=None,
        use_slugs=True,
        flatten_custom_fields=True,
        **kwargs
    ):

        nb_url = nb_url or os.environ.get("NB_URL", "http://localhost:8080")
        nb_token = nb_token or os.environ.get(
            "NB_TOKEN", "0123456789abcdef0123456789abcdef01234567"
        )
        headers = {"Authorization": "Token {}".format(nb_token)}

        # Create dict of hosts using 'devices' from NetBox
        r = requests.get("{}/api/dcim/devices/?limit=0".format(nb_url), headers=headers)
        r.raise_for_status()
        nb_devices = r.json()

        devices = {}
        for d in nb_devices["results"]:

            # Create temporary dict
            temp = {}

            # Add value for IP address
            if d.get("primary_ip", {}):
                temp["hostname"] = d["primary_ip"]["address"].split("/")[0]

            # Add values that don't have an option for 'slug'
            temp["serial"] = d["serial"]
            temp["vendor"] = d["device_type"]["manufacturer"]["name"]
            temp["asset_tag"] = d["asset_tag"]

            if flatten_custom_fields:
                for cf, value in d["custom_fields"].items():
                    temp[cf] = value
            else:
                temp["custom_fields"] = d["custom_fields"]

            # Add values that do have an option for 'slug'
            if use_slugs:
                temp["site"] = d["site"]["slug"]
                temp["role"] = d["device_role"]["slug"]
                temp["model"] = d["device_type"]["slug"]

                # Attempt to add 'platform' based of value in 'slug'
                temp["platform"] = d["platform"]["slug"] if d["platform"] else None

            else:
                temp["site"] = d["site"]["name"]
                temp["role"] = d["device_role"]
                temp["model"] = d["device_type"]
                temp["platform"] = d["platform"]

            # Assign temporary dict to outer dict
            devices[d["name"]] = temp

        # Pass the data back to the parent class
        super().__init__(devices, None, **kwargs)
