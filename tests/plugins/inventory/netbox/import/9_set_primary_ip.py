#!/usr/bin/env python3

import pynetbox
from nb_connect import *

if __name__ == "__main__":
    devices = nb.dcim.devices.all()

    for index, device in enumerate(devices):

        device.primary_ip4 = index + 1
        try:
            device.save()

            print(
                "\n{}. Device '{}' was set with primary IP".format(
                    index + 1, device.name
                )
            )

        except pynetbox.lib.query.RequestError as e:
            print(e.error)
