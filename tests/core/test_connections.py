from typing import Any, Dict, Optional

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin, Connections
from nornir.core.exceptions import (
    ConnectionAlreadyOpen,
    ConnectionNotOpen,
    ConnectionPluginAlreadyRegistered,
    ConnectionPluginNotRegistered,
)
from nornir.core.task import Result
from nornir.init_nornir import register_default_connection_plugins

import pytest


class DummyConnectionPlugin(ConnectionPlugin):
    name = "dummy"

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> Any:
        self.state["something"] = "something"
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.platform = platform
        self.extras = extras
        self.configuration = configuration
        return True

    def close(self) -> None:
        self.connection = False


class AnotherDummyConnectionPlugin(DummyConnectionPlugin):
    name = "another_dummy"


class FailingConnection(ConnectionPlugin):
    name = "failing"

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> Any:
        self.state["something"] = "something"
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.platform = platform
        self.extras = extras
        self.configuration = configuration
        return True

    def close(self):
        pass


def open_and_close_connection(task):
    task.host.open_connection("dummy", task.nornir.config)
    assert "dummy" in task.host.connections
    task.host.close_connection("dummy")
    assert "dummy" not in task.host.connections


def open_and_close_connection_same_plugin_different_name(task):
    conn_name = "another-connection-using-dummy-plugin"
    task.host.open_connection(conn_name, task.nornir.config, plugin_name="dummy")
    assert isinstance(task.host.connections[conn_name], DummyConnectionPlugin)
    task.host.close_connection(conn_name)
    assert conn_name not in task.host.connections


def open_connection_twice(task):
    task.host.open_connection("dummy", task.nornir.config)
    assert "dummy" in task.host.connections
    try:
        task.host.open_connection("dummy", task.nornir.config)
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


def dummy_task(task):
    task.get_connection(DummyConnectionPlugin)
    return Result(host=task.host, result="ok")


def dummy_failing_task_manual_conn(task):
    try:
        task.get_connection(DummyConnectionPlugin)
    except ConnectionNotOpen:
        assert not task.host.connections
        return Result(host=task.host, result="ok")
    except Exception:
        pytest.fail()


def failing_conn_task(task):
    task.get_connection(FailingConnection)
    return Result(host=task.host, result="ok")


def validate_params(task, conn, params):
    task.host.get_connection(conn, task.nornir.config)
    for k, v in params.items():
        assert getattr(task.host.connections[conn], k) == v


class Test(object):
    @classmethod
    def setup_class(cls):
        Connections.deregister_all()
        Connections.register(DummyConnectionPlugin)
        Connections.register(DummyConnectionPlugin, "dummy2")
        Connections.register(DummyConnectionPlugin, "dummy_no_overrides")

    def test_open_and_close_connection(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_and_close_connection, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_open_and_close_connection_same_plugin_different_name(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_and_close_connection_same_plugin_different_name)
        assert len(r) == 1
        assert not r.failed

    def test_open_connection_twice(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_connection_twice, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_auto_two_connections_dummy_plugin(self, nornir):
        with nornir.filter(name="dev2.group_1") as nr:
            r1 = nr.run(task=dummy_task)
            assert r1["dev2.group_1"].result == "ok"
            r2 = nr.run(task=dummy_task, conn_name="secondary_dummy")
            assert r2["dev2.group_1"].result == "ok"
            assert len(nr.inventory.hosts["dev2.group_1"].connections) == 2
        assert len(nr.inventory.hosts["dev2.group_1"].connections) == 0

    def test_close_not_opened_connection(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=close_not_opened_connection, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_failing_connection(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        nr.run(task=failing_conn_task, num_workers=1)
        assert len(nr.inventory.hosts["dev2.group_1"].connections) == 0

    def test_failing_task_manual_connection(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        nr.run(task=dummy_failing_task_manual_conn, autoconnect=False, num_workers=1)
        assert len(nr.inventory.hosts["dev2.group_1"].connections) == 0

    def test_context_manager(self, nornir):
        with nornir.filter(name="dev2.group_1") as nr:
            nr.run(task=dummy_task)
            assert "dummy" in nr.inventory.hosts["dev2.group_1"].connections
        assert "dummy" not in nr.inventory.hosts["dev2.group_1"].connections

    def test_validate_params_simple(self, nornir):
        params = {
            "hostname": "dev2.group_1",
            "username": "root",
            "password": "from_group1",
            "port": 22,
            "platform": "junos",
            "extras": {},
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
        params = {
            "port": 22,
            "hostname": "dummy_from_parent_group",
            "username": "root",
            "password": "from_group1",
            "platform": "junos",
            "extras": {"blah": "from_group"},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=validate_params, conn="dummy", params=params, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_validate_params_overrides_groups(self, nornir):
        params = {
            "port": 22,
            "hostname": "dummy2_from_parent_group",
            "username": "dummy2_from_host",
            "password": "from_group1",
            "platform": "junos",
            "extras": {"blah": "from_group"},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=validate_params, conn="dummy2", params=params, num_workers=1)
        assert len(r) == 1
        assert not r.failed


class TestConnectionPluginsRegistration(object):
    def setup_method(self, method):
        Connections.deregister_all()
        Connections.register(DummyConnectionPlugin)
        Connections.register(AnotherDummyConnectionPlugin)

    def teardown_method(self, method):
        Connections.deregister_all()
        register_default_connection_plugins()

    def test_count(self):
        assert len(Connections.available) == 2

    def test_register_new(self):
        Connections.register(DummyConnectionPlugin, "new_dummy")
        assert "new_dummy" in Connections.available

    def test_register_already_registered_same(self):
        Connections.register(DummyConnectionPlugin)
        assert Connections.available["dummy"] == DummyConnectionPlugin

    def test_register_already_registered_new(self):
        with pytest.raises(ConnectionPluginAlreadyRegistered):
            Connections.register(AnotherDummyConnectionPlugin, "dummy")

    def test_deregister_existing(self):
        Connections.deregister("dummy")
        assert len(Connections.available) == 1
        assert "dummy" not in Connections.available

    def test_deregister_nonexistent(self):
        with pytest.raises(ConnectionPluginNotRegistered):
            Connections.deregister("nonexistent_dummy")

    def test_deregister_all(self):
        Connections.deregister_all()
        assert Connections.available == {}

    def test_get_plugin(self):
        assert Connections.get_plugin("dummy") == DummyConnectionPlugin
        assert Connections.get_plugin("another_dummy") == AnotherDummyConnectionPlugin
        assert len(Connections.available) == 2

    def test_nonexistent_plugin(self):
        with pytest.raises(ConnectionPluginNotRegistered):
            Connections.get_plugin("nonexistent_dummy")
