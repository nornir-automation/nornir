import os
import subprocess
import time

from nornir.plugins.inventory import nsot

import pytest


def transform_function(host):
    attrs = ["user", "password"]
    for a in attrs:
        if a in host.data:
            host["nornir_{}".format(a)] = host.data[a]


@pytest.fixture(scope="module")
def inv(request):
    """Start/Stop containers needed for the tests."""

    def fin():
        subprocess.check_call(
            ["make", "stop_nsot"], stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )

    request.addfinalizer(fin)

    subprocess.check_call(["make", "start_nsot"], stdout=subprocess.PIPE)

    if os.getenv("TRAVIS"):
        time.sleep(10)
    else:
        time.sleep(3)

    return nsot.NSOTInventory(transform_function=transform_function)


@pytest.mark.usefixtures("inv")
class Test(object):

    def test_inventory(self, inv):
        assert len(inv.hosts) == 4
        assert len(inv.filter(site="site1").hosts) == 2
        assert len(inv.filter(os="junos").hosts) == 2
        assert len(inv.filter(site="site1", os="junos").hosts) == 1

    def test_transform_function(self, inv):
        for host in inv.hosts.values():
            assert host["user"] == host["nornir_user"]
            assert host["password"] == host["nornir_password"]
