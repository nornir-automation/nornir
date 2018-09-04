import json
import os

from nornir.plugins.inventory import nsot

# We need import below to load fixtures
import pytest  # noqa


BASE_PATH = os.path.join(os.path.dirname(__file__), "nsot")


def get_inv(requests_mock, case, **kwargs):
    for i in ["interfaces", "sites", "devices"]:
        with open("{}/{}/{}.json".format(BASE_PATH, case, i), "r") as f:
            requests_mock.get(
                "http://localhost:8990/api/{}".format(i),
                json=json.load(f),
                headers={"Content-type": "application/json"},
            )
    return nsot.NSOTInventory.deserialize(**kwargs)


def transform_function(host):
    attrs = ["user", "password"]
    for a in attrs:
        if a in host.data:
            host["modified_{}".format(a)] = host.data[a]


class Test(object):
    def test_inventory(self, requests_mock):
        inv = get_inv(requests_mock, "1.3.0", transform_function=transform_function)
        assert len(inv.hosts) == 4
        assert len(inv.filter(site="site1").hosts) == 2
        assert len(inv.filter(os="junos").hosts) == 2
        assert len(inv.filter(site="site1", os="junos").hosts) == 1

    def test_transform_function(self, requests_mock):
        inv = get_inv(requests_mock, "1.3.0", transform_function=transform_function)
        for host in inv.hosts.values():
            assert host["user"] == host["modified_user"]
            assert host["password"] == host["modified_password"]
