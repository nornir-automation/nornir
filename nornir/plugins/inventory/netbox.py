import os, json, pynetbox
from builtins import super
from nornir.core.inventory import Inventory


class NBInventory(Inventory):
    def __init__(self, url="", token="", **kwargs):

        url = url or os.environ.get("NB_URL", "http://localhost:8080")
        token = token or os.environ.get(
            "NB_TOKEN", "0123456789abcdef0123456789abcdef01234567"
        )
        nb = pynetbox.api(url, token)

        # Create dict of hosts using 'devices' from NetBox
        devices = {}
        nb_devices = nb.dcim.devices.all()
        for item in nb_devices:

            # Serialize item into temporary dict
            temp = item.serialize()

            # Get value to use for key in outer dict
            key = temp["name"]

            # Delete key 'name' from dict if exists
            if temp["name"]:
                del temp["name"]

            # Populate outer dict value with previously determined key
            devices[key] = temp

        # Create group based of 'device_roles' from NetBox
        roles = {}
        nb_roles = nb.dcim.device_roles.all()
        for item in nb_roles:

            # Serialize item into temporary dict
            temp = item.serialize()

            # Get value to use for key in outer dict
            key = temp["slug"]

            # Delete key 'name' from dict if exists
            if temp["name"]:
                del temp["name"]

            # Populate outer dict value with previously determined key
            roles[key] = temp

        # passing the data to the parent class so the data is
        # transformed into actual Host/Group objects
        super().__init__(devices, roles, **kwargs)
