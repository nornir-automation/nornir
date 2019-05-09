import json
import os

from nornir.core.deserializer.inventory import Inventory
from nornir.plugins.inventory import netbox

# We need import below to load fixtures
import pytest  # noqa


BASE_PATH = os.path.join(os.path.dirname(__file__), "netbox")


def get_inv(requests_mock, case, pagination, **kwargs):
    if not pagination:
        with open(f"{BASE_PATH}/{case}/mocked/devices.json", "r") as f:
            requests_mock.get(
                "http://localhost:8080/api/dcim/devices/?limit=0",
                json=json.load(f),
                headers={"Content-type": "application/json"},
            )
    else:
        for offset in range(3):
            with open(f"{BASE_PATH}/{case}/mocked/devices-{offset}.json", "r") as f:
                url = "http://localhost:8080/api/dcim/devices/?limit=0"
                requests_mock.get(
                    f"{url}&offset={offset}" if offset else url,
                    json=json.load(f),
                    headers={"Content-type": "application/json"},
                )
    return netbox.NBInventory.deserialize(**kwargs)


def transform_function(host):
    vendor_map = {"Cisco": "ios", "Juniper": "junos"}
    host["platform"] = vendor_map[host["vendor"]]


class Test(object):
    def test_inventory(self, requests_mock):
        inv = get_inv(requests_mock, "2.3.5", False)
        with open("{}/{}/expected.json".format(BASE_PATH, "2.3.5"), "r") as f:
            expected = json.load(f)
        assert expected == Inventory.serialize(inv).dict()

    def test_inventory_pagination(self, requests_mock):
        inv = get_inv(requests_mock, "2.3.5", True)
        with open("{}/{}/expected.json".format(BASE_PATH, "2.3.5"), "r") as f:
            expected = json.load(f)
        assert expected == Inventory.serialize(inv).dict()

    def test_transform_function(self, requests_mock):
        inv = get_inv(
            requests_mock, "2.3.5", False, transform_function=transform_function
        )
        #  with open(
        #      "{}/{}/expected_transform_function.json".format(BASE_PATH, "2.3.5"), "w"
        #  ) as f:
        #      f.write(InventorySerializer.serialize(inv).json())
        with open(
            "{}/{}/expected_transform_function.json".format(BASE_PATH, "2.3.5"), "r"
        ) as f:
            expected = json.load(f)
        assert expected == Inventory.serialize(inv).dict()
