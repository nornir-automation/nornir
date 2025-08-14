from typing import Any, Dict, Optional

import pytest

from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.core.exceptions import (
    ConnectionAlreadyOpen,
    ConnectionNotOpen,
    PluginAlreadyRegistered,
    PluginNotRegistered,
)
from nornir.core.plugins.connections import ConnectionPluginRegister
from nornir.core.task import Task


class DummyConnectionPlugin:
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


class FailedConnection(Exception):
    pass


class FailedConnectionPlugin:
    name = "fail"

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
        raise FailedConnection(f"Failed to open connection to {hostname}:{port}")

    def close(self) -> None:
        pass

    @property
    def connection(self) -> Any:
        """Used to fullfill protocol specs."""


def open_and_close_connection(task: Task, nornir_config: Config) -> None:
    task.host.open_connection("dummy", nornir_config)
    assert "dummy" in task.host.connections
    task.host.close_connection("dummy")
    assert "dummy" not in task.host.connections


def open_connection_twice(task: Task, nornir_config: Config) -> None:
    task.host.open_connection("dummy", nornir_config)
    assert "dummy" in task.host.connections
    try:
        task.host.open_connection("dummy", nornir_config)
        raise Exception("I shouldn't make it here")
    except ConnectionAlreadyOpen:
        task.host.close_connection("dummy")
        assert "dummy" not in task.host.connections


def close_not_opened_connection(task: Task) -> None:
    assert "dummy" not in task.host.connections
    try:
        task.host.close_connection("dummy")
        raise Exception("I shouldn't make it here")
    except ConnectionNotOpen:
        assert "dummy" not in task.host.connections


def failed_connection(task: Task, nornir_config: Config) -> None:
    task.host.open_connection(FailedConnectionPlugin.name, nornir_config)


def a_task(task: Task, nornir_config: Config) -> None:
    task.host.get_connection("dummy", nornir_config)


def validate_params(task: Task, conn: str, params: Dict[str, Any], nornir_config: Config) -> None:
    task.host.get_connection(conn, nornir_config)
    for k, v in params.items():
        assert getattr(task.host.connections[conn], k) == v


class Test:
    @classmethod
    def setup_class(cls) -> None:
        ConnectionPluginRegister.deregister_all()
        ConnectionPluginRegister.register("dummy", DummyConnectionPlugin)
        ConnectionPluginRegister.register("dummy2", DummyConnectionPlugin)
        ConnectionPluginRegister.register("dummy_no_overrides", DummyConnectionPlugin)
        ConnectionPluginRegister.register(FailedConnectionPlugin.name, FailedConnectionPlugin)

    def test_open_and_close_connection(self, nornir: Nornir) -> None:
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_and_close_connection, nornir_config=nornir.config)
        assert len(r) == 1
        assert not r.failed

    def test_open_connection_twice(self, nornir: Nornir) -> None:
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=open_connection_twice, nornir_config=nornir.config)
        assert len(r) == 1
        assert not r.failed

    def test_close_not_opened_connection(self, nornir: Nornir) -> None:
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(task=close_not_opened_connection)
        assert len(r) == 1
        assert not r.failed

    def test_failed_connection(self, nornir: Nornir) -> None:
        nr = nornir.filter(name="dev2.group_1")
        nr.run(task=failed_connection, nornir_config=nornir.config)
        assert FailedConnectionPlugin.name not in nornir.inventory.hosts["dev2.group_1"].connections

    def test_context_manager(self, nornir: Nornir) -> None:
        with nornir.filter(name="dev2.group_1") as nr:
            nr.run(task=a_task, nornir_config=nornir.config)
            assert "dummy" in nr.inventory.hosts["dev2.group_1"].connections
        assert "dummy" not in nr.inventory.hosts["dev2.group_1"].connections

    def test_validate_params_simple(self, nornir: Nornir) -> None:
        params = {
            "hostname": "localhost",
            "username": "root",
            "password": "from_group1",
            "port": 65021,
            "platform": "junos",
            "extras": {},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(
            task=validate_params,
            conn="dummy_no_overrides",
            params=params,
            nornir_config=nornir.config,
        )
        assert len(r) == 1
        assert not r.failed

    def test_validate_params_overrides(self, nornir: Nornir) -> None:
        params = {
            "port": 65021,
            "hostname": "dummy_from_parent_group",
            "username": "root",
            "password": "from_group1",
            "platform": "junos",
            "extras": {"blah": "from_group"},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(
            task=validate_params,
            conn="dummy",
            params=params,
            nornir_config=nornir.config,
        )
        assert len(r) == 1
        assert not r.failed

    def test_validate_params_overrides_groups(self, nornir: Nornir) -> None:
        params = {
            "port": 65021,
            "hostname": "dummy2_from_parent_group",
            "username": "dummy2_from_host",
            "password": "from_group1",
            "platform": "junos",
            "extras": {"blah": "from_group"},
        }
        nr = nornir.filter(name="dev2.group_1")
        r = nr.run(
            task=validate_params,
            conn="dummy2",
            params=params,
            nornir_config=nornir.config,
        )
        assert len(r) == 1
        assert not r.failed


class TestConnectionPluginsRegistration:
    def setup_method(self) -> None:
        ConnectionPluginRegister.deregister_all()
        ConnectionPluginRegister.register("dummy", DummyConnectionPlugin)
        ConnectionPluginRegister.register("another_dummy", AnotherDummyConnectionPlugin)

    def teardown_method(self) -> None:
        ConnectionPluginRegister.deregister_all()
        ConnectionPluginRegister.auto_register()

    def test_count(self) -> None:
        assert len(ConnectionPluginRegister.available) == 2

    def test_register_new(self) -> None:
        ConnectionPluginRegister.register("new_dummy", DummyConnectionPlugin)
        assert "new_dummy" in ConnectionPluginRegister.available

    def test_register_already_registered_same(self) -> None:
        ConnectionPluginRegister.register("dummy", DummyConnectionPlugin)
        assert ConnectionPluginRegister.available["dummy"] == DummyConnectionPlugin

    def test_register_already_registered_new(self) -> None:
        with pytest.raises(PluginAlreadyRegistered):
            ConnectionPluginRegister.register("dummy", AnotherDummyConnectionPlugin)

    def test_deregister_existing(self) -> None:
        ConnectionPluginRegister.deregister("dummy")
        assert len(ConnectionPluginRegister.available) == 1
        assert "dummy" not in ConnectionPluginRegister.available

    def test_deregister_nonexistent(self) -> None:
        with pytest.raises(PluginNotRegistered):
            ConnectionPluginRegister.deregister("nonexistent_dummy")

    def test_deregister_all(self) -> None:
        ConnectionPluginRegister.deregister_all()
        assert ConnectionPluginRegister.available == {}

    def test_get_plugin(self) -> None:
        assert ConnectionPluginRegister.get_plugin("dummy") == DummyConnectionPlugin
        assert ConnectionPluginRegister.get_plugin("another_dummy") == AnotherDummyConnectionPlugin
        assert len(ConnectionPluginRegister.available) == 2

    def test_nonexistent_plugin(self) -> None:
        with pytest.raises(PluginNotRegistered):
            ConnectionPluginRegister.get_plugin("nonexistent_dummy")
