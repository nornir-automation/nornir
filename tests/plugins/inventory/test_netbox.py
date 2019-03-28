import json
import os

from nornir.core.deserializer.inventory import Inventory
from nornir.plugins.inventory import netbox

# We need import below to load fixtures
import pytest  # noqa


BASE_PATH = os.path.join(os.path.dirname(__file__), "netbox")


def get_inv(requests_mock, case, **kwargs):
    for num in range(1, 4):
        with open(f"{BASE_PATH}/{case}/mocked/devices_{num}.json", "r") as f:
            requests_mock.get(
                "http://localhost:8080/api/dcim/devices/?limit=3",
                json=json.load(f),
                headers={"Content-type": "application/json"},
            )

        # Something needs to be added here to combine the mocked requests
        # within the for loop and return one set of kwargs

    return netbox.NBInventory.deserialize(**kwargs)


class Test(object):
    def test_inventory(self, requests_mock):
        inv = get_inv(requests_mock, "2.5.8")
        with open(f"{BASE_PATH}/{'2.5.8'}/expected.json", "r") as f:
            expected = json.load(f)
        assert expected == Inventory.serialize(inv).dict()
