#!/usr/bin/env python3

import collections
from netbox_tools import NetBoxTools

conn_details = "import/netbox_connect.yaml"

definitions = collections.OrderedDict()
definitions["dcim."] = [
    "sites",
    "device_roles",
    "manufacturers",
    "device_types",
    "platforms",
    "devices",
    "interfaces",
]
definitions["ipam."] = ["ip_addresses"]

if __name__ == "__main__":

    # Create NetBoxTools object and connect
    nb_tools = NetBoxTools(conn_details)
    nb_tools.connect()

    # Iterate through all model-endpoint combinations
    for model, endpoint in definitions.items():
        for item in endpoint:
            nb_tools.load_json("import/json/" + item + ".json")
            nb_tools.import_data(model, item)

    # Get all devices and set primary_ip4
    devices = nb_tools.nb.dcim.devices.all()
    for index, device in enumerate(devices):
        device.primary_ip4 = index + 1

        try:
            device.save()
            print(
                "\n{}. Device '{}' was set with primary IP".format(
                    index + 1, device.name
                )
            )
        except netbox_tools.pynetbox.RequestError as e:
            print(e.error)
