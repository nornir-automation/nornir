from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

from nornir import InitNornir
from nornir.core.configuration import Config
from nornir.core.exceptions import (
    ConnectionPluginAmbiguousError,
    ConnectionPluginContractError,
    ConnectionPluginNotSyncError,
    PluginAlreadyRegistered,
)
from nornir.core.inventory import Defaults, Groups, Host, Hosts, Inventory
from nornir.core.plugins.connections import (
    CAPABILITY_CONNECTIONS_PLUGIN_PATH,
    AsyncCapabilityConnectionPlugin,
    CapabilityConnectionPlugin,
    CapabilityConnectionPluginRegister,
    ConnectionCapability,
    ConnectionPlugin,
    ConnectionPluginRegister,
    DualCapabilityConnectionPlugin,
    SyncCapabilityConnectionPlugin,
)


class BasePlugin:
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"sync"})

    @property
    def connection(self) -> Any:
        return None


class SyncPlugin(BasePlugin):
    opened = 0
    closed = 0

    def open(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        SyncPlugin.opened += 1

    def close(self) -> None:
        SyncPlugin.closed += 1


class AsyncPlugin(BasePlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"asyncio"})

    async def aopen(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        await asyncio.sleep(0)

    async def aclose(self) -> None:
        await asyncio.sleep(0)


class DualPlugin(SyncPlugin, AsyncPlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"sync", "asyncio"})


class OtherSyncPlugin(SyncPlugin):
    pass


class FakeEntryPoint:
    def __init__(self, name: str, plugin: type[CapabilityConnectionPlugin]) -> None:
        self.name = name
        self.plugin = plugin

    def load(self) -> type[CapabilityConnectionPlugin]:
        return self.plugin


@pytest.fixture(autouse=True)
def isolated_connection_registries() -> Iterator[None]:
    legacy_available = ConnectionPluginRegister.available
    capability_available = CapabilityConnectionPluginRegister.available
    legacy = legacy_available.copy()
    capability = capability_available.copy()
    legacy_available.clear()
    capability_available.clear()
    SyncPlugin.opened = 0
    SyncPlugin.closed = 0
    yield
    legacy_available.clear()
    legacy_available.update(legacy)
    capability_available.clear()
    capability_available.update(capability)
    ConnectionPluginRegister.available = legacy_available
    CapabilityConnectionPluginRegister.available = capability_available


def test_protocols_are_structural_and_async_only_needs_no_sync_stubs() -> None:
    base: CapabilityConnectionPlugin = BasePlugin()
    sync: SyncCapabilityConnectionPlugin = SyncPlugin()
    async_only: AsyncCapabilityConnectionPlugin = AsyncPlugin()
    dual: DualCapabilityConnectionPlugin = DualPlugin()
    legacy: ConnectionPlugin = SyncPlugin()
    legacy_dual: ConnectionPlugin = DualPlugin()

    assert base.get_capabilities() == frozenset({"sync"})
    assert sync.get_capabilities() == frozenset({"sync"})
    assert async_only.get_capabilities() == frozenset({"asyncio"})
    assert dual.get_capabilities() == frozenset({"sync", "asyncio"})
    assert legacy.connection is None
    assert legacy_dual.connection is None
    assert not hasattr(async_only, "open")
    assert not hasattr(async_only, "close")


def test_capability_registry_has_isolated_storage() -> None:
    assert CapabilityConnectionPluginRegister.available is not ConnectionPluginRegister.available

    CapabilityConnectionPluginRegister.register("sync", SyncPlugin)

    assert CapabilityConnectionPluginRegister.get_plugin("sync") is SyncPlugin
    assert "sync" not in ConnectionPluginRegister.available


def test_programmatic_registration_is_idempotent_for_the_same_plugin() -> None:
    CapabilityConnectionPluginRegister.register("sync", SyncPlugin)
    CapabilityConnectionPluginRegister.register("sync", SyncPlugin)

    assert CapabilityConnectionPluginRegister.available == {"sync": SyncPlugin}
    with pytest.raises(PluginAlreadyRegistered):
        CapabilityConnectionPluginRegister.register("sync", OtherSyncPlugin)


@pytest.mark.parametrize("plugin", [SyncPlugin, AsyncPlugin, DualPlugin])
def test_auto_discovery_supports_every_capability_combination(
    monkeypatch: pytest.MonkeyPatch, plugin: type[CapabilityConnectionPlugin]
) -> None:
    def entry_points(*, group: str) -> list[FakeEntryPoint]:
        assert group == CAPABILITY_CONNECTIONS_PLUGIN_PATH
        return [FakeEntryPoint("transport", plugin)]

    monkeypatch.setattr("nornir.core.plugins.register.metadata.entry_points", entry_points)

    CapabilityConnectionPluginRegister.auto_register()

    assert CapabilityConnectionPluginRegister.available == {"transport": plugin}
    assert ConnectionPluginRegister.available == {}


def test_init_nornir_discovers_both_connection_groups_before_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def discover_legacy() -> None:
        calls.append("legacy")

    def discover_capability() -> None:
        calls.append("capability")

    def load_inventory(config: Config) -> Inventory:
        calls.append("inventory")
        return Inventory(hosts=Hosts(), groups=Groups(), defaults=Defaults())

    monkeypatch.setattr(ConnectionPluginRegister, "auto_register", discover_legacy)
    monkeypatch.setattr(CapabilityConnectionPluginRegister, "auto_register", discover_capability)
    monkeypatch.setattr("nornir.init_nornir.load_inventory", load_inventory)

    InitNornir(logging={"enabled": False})

    assert calls == ["legacy", "capability", "inventory"]


@pytest.mark.parametrize("legacy_first", [True, False])
@pytest.mark.parametrize("same_class", [True, False])
def test_cross_registry_duplicates_are_ambiguous_regardless_of_registration_order(
    legacy_first: bool, same_class: bool
) -> None:
    capability_plugin = SyncPlugin if same_class else OtherSyncPlugin
    if legacy_first:
        ConnectionPluginRegister.register("duplicate", SyncPlugin)
        CapabilityConnectionPluginRegister.register("duplicate", capability_plugin)
    else:
        CapabilityConnectionPluginRegister.register("duplicate", capability_plugin)
        ConnectionPluginRegister.register("duplicate", SyncPlugin)

    with pytest.raises(ConnectionPluginAmbiguousError):
        Host("host").get_connection("duplicate", Config())
    assert SyncPlugin.opened == 0


def test_duplicate_introduced_after_caching_blocks_get_but_not_cleanup() -> None:
    host = Host("host")
    CapabilityConnectionPluginRegister.register("transport", SyncPlugin)
    host.get_connection("transport", Config())
    ConnectionPluginRegister.register("transport", SyncPlugin)

    with pytest.raises(ConnectionPluginAmbiguousError):
        host.get_connection("transport", Config())

    host.close_connection("transport")
    assert SyncPlugin.closed == 1


class ReportingRaises(BasePlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        msg = "reporting failed"
        raise RuntimeError(msg)


class EmptyCapabilities(BasePlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset()


class MissingClose(BasePlugin):
    def open(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        SyncPlugin.opened += 1


class MissingOpen(BasePlugin):
    def close(self) -> None:
        SyncPlugin.closed += 1


class InaccessibleOpen(BasePlugin):
    @property
    def open(self) -> Any:
        msg = "open could not be accessed"
        raise RuntimeError(msg)

    def close(self) -> None:
        SyncPlugin.closed += 1


class MissingAsyncClose(BasePlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"asyncio"})

    async def aopen(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        await asyncio.sleep(0)


class MissingAsyncOpen(BasePlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"asyncio"})

    async def aclose(self) -> None:
        await asyncio.sleep(0)


class DualMissingAsyncClose(SyncPlugin):
    async def aopen(
        self,
        hostname: str | None,
        username: str | None,
        password: str | None,
        port: int | None,
        platform: str | None,
        extras: dict[str, Any] | None = None,
        configuration: Config | None = None,
    ) -> None:
        await asyncio.sleep(0)

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"sync", "asyncio"})


class MissingReporting:
    @property
    def connection(self) -> Any:
        return None


class UnknownCapabilities(BasePlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return cast("frozenset[ConnectionCapability]", frozenset({"threads"}))


class ListCapabilities(BasePlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return cast("frozenset[ConnectionCapability]", ["sync"])


class ProbingInvalidPlugin(MissingClose):
    @property
    def connection(self) -> Any:
        msg = "connection was probed before opening"
        raise AssertionError(msg)


@pytest.mark.parametrize(
    "plugin",
    [
        cast("type[CapabilityConnectionPlugin]", MissingReporting),
        ReportingRaises,
        EmptyCapabilities,
        UnknownCapabilities,
        ListCapabilities,
        ProbingInvalidPlugin,
        MissingOpen,
        MissingClose,
        cast("type[CapabilityConnectionPlugin]", InaccessibleOpen),
        MissingAsyncOpen,
        MissingAsyncClose,
        DualMissingAsyncClose,
    ],
)
def test_invalid_declarations_fail_before_io_or_connection_property_access(
    plugin: type[CapabilityConnectionPlugin],
) -> None:
    CapabilityConnectionPluginRegister.register("invalid", plugin)

    with pytest.raises(ConnectionPluginContractError):
        Host("host").open_connection("invalid", Config())
    assert SyncPlugin.opened == 0


class AsyncDeclarationWithExtraSyncMethods(SyncPlugin, AsyncPlugin):
    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"asyncio"})


def test_undeclared_extra_methods_do_not_enable_sync_mode() -> None:
    CapabilityConnectionPluginRegister.register("async-only", AsyncDeclarationWithExtraSyncMethods)

    with pytest.raises(ConnectionPluginNotSyncError):
        Host("host").open_connection("async-only", Config())
    assert SyncPlugin.opened == 0
