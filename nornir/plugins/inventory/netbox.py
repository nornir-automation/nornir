import os
import pynetbox
from builtins import super
from nornir.core.inventory import Inventory


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
        nb_obj = pynetbox.api(nb_url, nb_token)

        # Create dict of hosts using 'devices' from NetBox
        devices = {}
        nb_devices = nb_obj.dcim.devices.all()
        for d in nb_devices:

            # Add values to temporary dict that don't have a 'slug' attribute
            temp = {}
            temp["site"] = d.site.name
            temp["serial"] = d.serial
            temp["vendor"] = d.device_type.manufacturer.name
            temp["asset_tag"] = d.asset_tag
            temp["nornir_host"] = str(d.primary_ip).split("/")[0]

            if flatten_custom_fields:
                for cf, value in d.custom_fields.items():
                    temp[cf] = value
            else:
                temp["custom_fields"] = d.custom_fields

            # Add values to temporary dict that do have a 'slug' attribute
            # This is determined based off of passed variable 'use_slugs'
            if use_slugs:
                temp["role"] = d.device_role.slug
                temp["model"] = d.device_type.slug

                # Attempt to add 'platform' based of value in 'slug'
                try:
                    temp["nornir_nos"] = d.platform.slug
                except AttributeError:
                    temp["nornir_nos"] = None
            else:
                temp["role"] = d.device_role
                temp["model"] = d.device_type
                temp["nornir_nos"] = d.platform

            # Copy temporary dict to outer dict
            devices[d.name] = temp

        # Pass the data back to the parent class
        super().__init__(devices, None, **kwargs)
