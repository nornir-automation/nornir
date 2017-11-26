import logging
import os
import subprocess

from brigade.core import Brigade
from brigade.plugins.inventory.simple import SimpleInventory

import pytest


logging.basicConfig(
    filename="tests.log",
    filemode='w',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)20s() - %(message)s',
)


@pytest.fixture(scope="session", autouse=True)
def containers(request):
    """Start/Stop containers needed for the tests."""
    logging.info("Starting containers")
    subprocess.check_call(["./tests/inventory_data/containers.sh", "start"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def fin():
        logging.info("Stopping containers")
        subprocess.check_call(["./tests/inventory_data/containers.sh", "stop"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    request.addfinalizer(fin)


@pytest.fixture(scope="session", autouse=True)
def brigade(request):
    """Initializes brigade"""
    dir_path = os.path.dirname(os.path.realpath(__file__))

    brigade = Brigade(
        inventory=SimpleInventory("{}/inventory_data/hosts.yaml".format(dir_path),
                                  "{}/inventory_data/groups.yaml".format(dir_path)),
        dry_run=True,
    )
    return brigade
