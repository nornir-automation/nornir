import json
import os

from nornir.core.deserializer.inventory import Inventory
from nornir.plugins.inventory import netbox

# We need import below to load fixtures
import pytest  # noqa


BASE_PATH = os.path.join(os.path.dirname(__file__), "netbox")


def get_inv(requests_mock, case, pagination, **kwargs):
    platform = (
        "platforms_conn_opts"
        if os.environ.get("NB_PLATFORM_AS_CONN_OPTS")
        else "platforms"
    )
    with open(f"{BASE_PATH}/{case}/mocked/{platform}.json", "r") as f:
        requests_mock.get(
            "http://localhost:8080/api/dcim/platforms/?limit=0",
            json=json.load(f),
            headers={"Content-type": "application/json"},
        )
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
    versions = ["2.3.5", "2.8.9"]

    def test_inventory(self, requests_mock):
        for version in self.versions:
            inv = get_inv(requests_mock, version, False)
            with open("{}/{}/expected.json".format(BASE_PATH, version), "r") as f:
                expected = json.load(f)
            assert expected == Inventory.serialize(inv).dict()

    def test_inventory_pagination(self, requests_mock):
        for version in self.versions:
            inv = get_inv(requests_mock, version, True)
            with open("{}/{}/expected.json".format(BASE_PATH, version), "r") as f:
                expected = json.load(f)
            assert expected == Inventory.serialize(inv).dict()

    def test_transform_function(self, requests_mock):
        for version in self.versions:
            inv = get_inv(
                requests_mock, version, False, transform_function=transform_function
            )
            with open(
                "{}/{}/expected_transform_function.json".format(BASE_PATH, version), "r"
            ) as f:
                expected = json.load(f)
            assert expected == Inventory.serialize(inv).dict()

    def test_inventory_use_platform_args(self, requests_mock):
        for version in self.versions:
            inv = get_inv(requests_mock, version, False, use_platform_args=True)
            with open(
                "{}/{}/expected_use_platform_args.json".format(BASE_PATH, version), "r"
            ) as f:
                expected = json.load(f)
            assert expected == Inventory.serialize(inv).dict()

    def test_inventory_use_platform_args_as_conn_opts(self, requests_mock):
        # Overload the Netbox Platform args and import them as connection options
        # instead of for their intended use for the NAPALM driver
        os.environ["NB_PLATFORM_AS_CONN_OPTS"] = "1"
        for version in self.versions:
            inv = get_inv(requests_mock, version, False, use_platform_args=True,)
            with open(
                "{}/{}/expected_use_platform_args_conn_opts.json".format(
                    BASE_PATH, version
                ),
                "r",
            ) as f:
                expected = json.load(f)
            assert expected == Inventory.serialize(inv).dict()
