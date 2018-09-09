import logging
import os
import subprocess

from nornir import InitNornir
from nornir.core.state import GlobalState

import pytest


global_data = GlobalState()


logging.basicConfig(
    filename="tests.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)20s() - %(message)s",
)


@pytest.fixture(scope="session", autouse=True)
def containers(request):
    """Start/Stop containers needed for the tests."""

    def fin():
        logging.info("Stopping containers")
        subprocess.check_call(
            ["./tests/inventory_data/containers.sh", "stop"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    request.addfinalizer(fin)

    try:
        fin()
    except Exception:
        pass
    logging.info("Starting containers")
    subprocess.check_call(
        ["./tests/inventory_data/containers.sh", "start"], stdout=subprocess.PIPE
    )


@pytest.fixture(scope="session", autouse=True)
def nornir(request):
    """Initializes nornir"""
    dir_path = os.path.dirname(os.path.realpath(__file__))

    nornir = InitNornir(
        inventory={
            "options": {
                "host_file": "{}/inventory_data/hosts.yaml".format(dir_path),
                "group_file": "{}/inventory_data/groups.yaml".format(dir_path),
                "defaults_file": "{}/inventory_data/defaults.yaml".format(dir_path),
            }
        },
        dry_run=True,
    )
    nornir.data = global_data
    return nornir


@pytest.fixture(scope="function", autouse=True)
def reset_failed_hosts():
    global_data.reset_failed_hosts()
