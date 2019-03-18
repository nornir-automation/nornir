from typing import Any, Dict, Optional

from nornir.core.configuration import Config
from nornir.core.connections import ConnectionPlugin, Connections
from nornir.core.exceptions import (
    ConnectionAlreadyOpen,
    ConnectionNotOpen,
    ConnectionPluginAlreadyRegistered,
    ConnectionPluginNotRegistered,
)
from nornir.init_nornir import register_default_connection_plugins

import pytest


class DummyConnectionPlugin(ConnectionPlugin):
    def open(
        self,
        hostname: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int],
        platform: Optional[str],
        extras: Optional[Dict[str, Any]] = None,
        configuration: Optional[Config] = None,
    ) -> None:
        self.connection = True
        self.state["something"] = "something"
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.platform = platform
        self.extras = extras
        self.configuration = configuration

    def close(self) -> None:
        self.connection = False


class AnotherDummyConnectionPlugin(DummyConnectionPlugin):
    pass


def open_and_close_connection(task):
    task.host.open_connection("dummy", task.nornir.config)
    assert "dummy" in task.host.connections
    task.host.close_connection("dummy")
    assert "dummy" not in task.host.connections


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


def a_task(task):
    task.host.get_connection("dummy", task.nornir.config)


def validate_params(task, conn, params):
    task.host.get_connection(conn, task.nornir.config)
    for k, v in params.items():
        assert getattr(task.host.connections[conn], k) == v


class Test(object):
    @classmethod
    def setup_class(cls):
        Connections.deregister_all()
        Connections.register("dummy", DummyConnectionPlugin)
        Connections.register("dummy2", DummyConnectionPlugin)
        Connections.register("dummy_no_overrides", DummyConnectionPlugin)

    def test_open_and_close_connection(self, nornir):
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_and_close_connection, num_workers=1)
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
        Connections.register("dummy", DummyConnectionPlugin)
        Connections.register("another_dummy", AnotherDummyConnectionPlugin)

    def teardown_method(self, method):
        Connections.deregister_all()
        register_default_connection_plugins()

    def test_count(self):
        assert len(Connections.available) == 2

    def test_register_new(self):
        Connections.register("new_dummy", DummyConnectionPlugin)
        assert "new_dummy" in Connections.available

    def test_register_already_registered_same(self):
        Connections.register("dummy", DummyConnectionPlugin)
        assert Connections.available["dummy"] == DummyConnectionPlugin

    def test_register_already_registered_new(self):
        with pytest.raises(ConnectionPluginAlreadyRegistered):
            Connections.register("dummy", AnotherDummyConnectionPlugin)

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
