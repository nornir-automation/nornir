from typing import Any, Dict, Optional

import pytest

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin, Connections
from nornir.core.exceptions import (
    ConnectionAlreadyOpen,
    ConnectionNotOpen,
    ConnectionPluginNotRegistered,
    ConnectionPluginAlreadyRegistered,
)
from nornir.core.task import Result
from nornir.plugins.connections import register_default_connection_plugins


class DummyConnectionPlugin(ConnectionPlugin):
    name = "dummy"

    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        connection_options: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        self.connection = True
        self.state["something"] = "something"
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.platform = platform
        self.connection_options = connection_options
        self.configuration = configuration

    def close(self) -> None:
        self.connection = False


class AnotherDummyConnectionPlugin(DummyConnectionPlugin):
    name = "another_dummy"


class NewDummyConnectionPlugin(DummyConnectionPlugin):
    name = "new_dummy"


class DuplicateDummyConnectionPlugin(DummyConnectionPlugin):
    name = "dummy"


def dummy_task(task) -> Result:
    task.get_connection(DummyConnectionPlugin.name)
    return Result(host=task.host, result="ok")


def open_and_close_connection(task):
    task.host.open_connection("dummy")
    assert "dummy" in task.host.connections
    task.host.close_connection("dummy")
    assert "dummy" not in task.host.connections


def open_and_close_connection_dummy_plugin_different_name(task):
    task.host.open_connection("another-connection-using-dummy-plugin", plugin="dummy")
    assert isinstance(
        task.host.connections["another-connection-using-dummy-plugin"],
        DummyConnectionPlugin,
    )
    task.host.close_connection("another-connection-using-dummy-plugin")
    assert "another-connection-using-dummy-plugin" not in task.host.connections


def open_and_close_two_connections_dummy_plugin(task):
    task.host.open_connection("dummy")
    task.host.open_connection("another-connection-using-dummy-plugin", plugin="dummy")
    assert isinstance(
        task.host.connections["another-connection-using-dummy-plugin"],
        DummyConnectionPlugin,
    )
    assert isinstance(task.host.connections["dummy"], DummyConnectionPlugin)
    assert len(task.host.connections) == 2
    task.host.close_connection("another-connection-using-dummy-plugin")
    task.host.close_connection("dummy")
    assert len(task.host.connections) == 0


def open_connection_twice(task):
    task.host.open_connection("dummy")
    assert "dummy" in task.host.connections
    with pytest.raises(ConnectionAlreadyOpen):
        task.host.open_connection("dummy")
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
    task.get_connection(DummyConnectionPlugin.name)


def validate_params(task, conn, params):
    task.get_connection(conn)
    for k, v in params.items():
        assert getattr(task.host.connections[conn], k) == v


class Test(object):
    @classmethod
    def setup_class(cls):
        Connections.deregister_all()
        Connections.register(DummyConnectionPlugin)
        Connections.register(AnotherDummyConnectionPlugin)

    def test_open_and_close_connection(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_and_close_connection, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_open_and_close_connection_dummy_plugin_different_name(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(
            task=open_and_close_connection_dummy_plugin_different_name, num_workers=1
        )
        assert len(r) == 1
        assert not r.failed

    def test_open_and_close_two_connections_dummy_plugin(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_and_close_two_connections_dummy_plugin, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_open_connection_twice(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_connection_twice, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_close_not_opened_connection(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=close_not_opened_connection, num_workers=1)
        assert len(r) == 1
        assert not r.failed

    def test_context_manager(self, nornir):
        with nornir.filter(name="dev2.group_1") as nr:
            nr.run(task=a_task)
            assert "dummy" in nr.inventory.hosts["dev2.group_1"].connections
        assert "dummy" not in nr.inventory.hosts["dev2.group_1"].connections
        nornir.data.reset_failed_hosts()

    def test_auto_two_connections_dummy_plugin(self, nornir):
        with nornir.filter(name="dev2.group_1") as nr:
            r1 = nr.run(task=dummy_task)
            assert r1["dev2.group_1"].result == "ok"
            r2 = nr.run(task=dummy_task, conn_name="secondary_dummy")
            assert r2["dev2.group_1"].result == "ok"
            assert len(nr.inventory.hosts["dev2.group_1"].connections) == 2
        assert len(nr.inventory.hosts["dev2.group_1"].connections) == 0

    def test_validate_params_simple(self, nornir):
        params = {
            "hostname": "127.0.0.1",
            "username": "root",
            "password": "docker",
            "port": 65002,
            "platform": "junos",
            "connection_options": {},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(
            task=validate_params, conn="another_dummy", params=params, num_workers=1
        )
        assert len(r) == 1
        assert not r.failed

    def test_validate_params_overrides(self, nornir):
        params = {
            "hostname": "overriden_hostname",
            "username": "root",
            "password": "docker",
            "port": None,
            "platform": "junos",
            "connection_options": {"awesome_feature": 1},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=validate_params, conn="dummy", params=params, num_workers=1)
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
        Connections.register(NewDummyConnectionPlugin)
        assert "new_dummy" in Connections.available

    def test_register_already_registered_same(self):
        Connections.register(DummyConnectionPlugin)
        assert Connections.available["dummy"] == DummyConnectionPlugin

    def test_register_already_registered_new(self):
        with pytest.raises(ConnectionPluginAlreadyRegistered):
            Connections.register(DuplicateDummyConnectionPlugin)

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
