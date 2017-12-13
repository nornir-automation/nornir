import subprocess
import time

from brigade.plugins.inventory import nsot

import pytest


def transform_function(host):
    attrs = ["user", "password"]
    for a in attrs:
        if a in host.data:
            host["brigade_{}".format(a)] = host.data[a]


@pytest.fixture(scope="module")
def inv(request):
    """Start/Stop containers needed for the tests."""
    def fin():
        subprocess.check_call(["make", "stop_nsot"],
                              stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    request.addfinalizer(fin)

    subprocess.check_call(["make", "start_nsot"],
                          stdout=subprocess.PIPE)
    time.sleep(3)  # nsot takes a while to start
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
            assert host["user"] == host["brigade_user"]
            assert host["password"] == host["brigade_password"]
