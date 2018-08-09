from typing import Any, Dict, Optional

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin
from nornir.core.exceptions import ConnectionAlreadyOpen, ConnectionNotOpen


class DummyConnectionPlugin(ConnectionPlugin):
    """
    This plugin connects to the device using the NAPALM driver and sets the
    relevant connection.

    Inventory:
        napalm_options: maps directly to ``optional_args`` when establishing the connection
        nornir_network_api_port: maps to ``optional_args["port"]``
        napalm_options["timeout"]: maps to ``timeout``.
    """

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        advanced_options: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        self.connection = True
        self.state["something"] = "something"
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.platform = platform
        self.advanced_options = advanced_options
        self.configuration = configuration

    def close(self) -> None:
        self.connection = False


def open_and_close_connection(task):
    task.host.open_connection("dummy")
    assert "dummy" in task.host.connections
    task.host.close_connection("dummy")
    assert "dummy" not in task.host.connections


def open_connection_twice(task):
    task.host.open_connection("dummy")
    assert "dummy" in task.host.connections
    try:
        task.host.open_connection("dummy")
        raise Exception("I shouldn't make it here")
    except ConnectionAlreadyOpen:
        task.host.close_connection("dummy")
        assert "dummy" not in task.host.connections


def close_not_opened_connection(task):
    assert "dummy" not in task.host.connections
    try:
        task.host.close_connection("dummy")
        raise Exception("I shouldn't make it here")
    except ConnectionNotOpen:
        assert "dummy" not in task.host.connections


def a_task(task):
    task.host.get_connection("dummy")


def validate_params(task, conn, params):
    task.host.get_connection(conn)
    for k, v in params.items():
        assert getattr(task.host.connections[conn], k) == v


class Test(object):
    def test_open_and_close_connection(self, nornir):
        nornir.data.available_connections["dummy"] = DummyConnectionPlugin
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_and_close_connection, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_open_connection_twice(self, nornir):
        nornir.data.available_connections["dummy"] = DummyConnectionPlugin
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_connection_twice, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_close_not_opened_connection(self, nornir):
        nornir.data.available_connections["dummy"] = DummyConnectionPlugin
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=close_not_opened_connection, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_context_manager(self, nornir):
        nornir.data.available_connections["dummy"] = DummyConnectionPlugin
        with nornir.filter(name="dev2.group_1") as nr:
            nr.run(task=a_task)
            assert "dummy" in nr.inventory.hosts["dev2.group_1"].connections
        assert "dummy" not in nr.inventory.hosts["dev2.group_1"].connections
        nornir.data.reset_failed_hosts()

    def test_validate_params_simple(self, nornir):
        nornir.data.available_connections["dummy_no_overrides"] = DummyConnectionPlugin
        params = {
            "hostname": "127.0.0.1",
            "username": "root",
            "password": "docker",
            "port": 65002,
            "platform": "junos",
            "advanced_options": {},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(
            task=validate_params,
            conn="dummy_no_overrides",
            params=params,
            num_workers=1,
        )
        assert len(r) == 1
        assert not r.failed

    def test_validate_params_overrides(self, nornir):
        nornir.data.available_connections["dummy"] = DummyConnectionPlugin
        params = {
            "hostname": "overriden_hostname",
            "username": "root",
            "password": "docker",
            "port": None,
            "platform": "junos",
            "advanced_options": {"awesome_feature": 1},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=validate_params, conn="dummy", params=params, num_workers=1)
        assert len(r) == 1
        assert not r.failed
