from __future__ import annotations

import asyncio
import copy
import pickle  # noqa: S403 - this test verifies trusted local Host serialization.
from typing import TYPE_CHECKING, Any, ClassVar

import pytest

if TYPE_CHECKING:
    from collections.abc import Coroutine, Iterator

from nornir.core.configuration import Config
from nornir.core.exceptions import (
    ConnectionAlreadyOpen,
    ConnectionNotOpen,
    ConnectionPluginAmbiguousError,
    ConnectionPluginContractError,
    ConnectionPluginNotAsyncError,
    ConnectionPluginNotSyncError,
)
from nornir.core.inventory import (
    ConnectionOptions,
    Defaults,
    Groups,
    Host,
    Hosts,
    Inventory,
)
from nornir.core.plugins.connections import (
    AsyncCapabilityConnectionPlugin,
    CapabilityConnectionPluginRegister,
    ConnectionCapability,
    ConnectionPlugin,
    ConnectionPluginRegister,
)


class LegacyPlugin:
    instances: ClassVar[list[Any]] = []

    def __init__(self) -> None:
        self.opened = 0
        self.closed = 0
        self.parameters: dict[str, Any] = {}
        self._connection = object()
        self.__class__.instances.append(self)

    @property
    def connection(self) -> object:
        return self._connection

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
        self.opened += 1
        self.parameters = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "port": port,
            "platform": platform,
            "extras": extras,
            "configuration": configuration,
        }

    def close(self) -> None:
        self.closed += 1

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
        raise AssertionError("legacy async extension must not be used")

    async def aclose(self) -> None:
        raise AssertionError("legacy async extension must not be used")


class SyncPlugin(LegacyPlugin):
    instances: ClassVar[list[Any]] = []

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"sync"})


class AsyncPlugin:
    instances: ClassVar[list[Any]] = []
    open_gate: ClassVar[asyncio.Event | None] = None
    open_started: ClassVar[asyncio.Event | None] = None
    close_gate: ClassVar[asyncio.Event | None] = None
    close_started: ClassVar[asyncio.Event | None] = None
    fail_open: ClassVar[bool] = False
    fail_close: ClassVar[bool] = False

    def __init__(self) -> None:
        self.opened = 0
        self.closed = 0
        self.open_cancelled = 0
        self.close_cancelled = 0
        self.parameters: dict[str, Any] = {}
        self._connection = object()
        self.__class__.instances.append(self)

    @property
    def connection(self) -> object:
        return self._connection

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
        self.opened += 1
        self.parameters = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "port": port,
            "platform": platform,
            "extras": extras,
            "configuration": configuration,
        }
        if self.open_started is not None:
            self.open_started.set()
        try:
            if self.open_gate is not None:
                await self.open_gate.wait()
            if self.fail_open:
                raise RuntimeError("open failed")
        except asyncio.CancelledError:
            self.open_cancelled += 1
            raise

    async def aclose(self) -> None:
        if self.close_started is not None:
            self.close_started.set()
        try:
            if self.close_gate is not None:
                await self.close_gate.wait()
            else:
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            self.close_cancelled += 1
            raise
        if self.fail_close:
            raise RuntimeError("close failed")
        self.closed += 1


class DualPlugin(SyncPlugin):
    instances: ClassVar[list[Any]] = []

    def __init__(self) -> None:
        super().__init__()
        self.async_opened = 0
        self.async_closed = 0

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return frozenset({"sync", "asyncio"})

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
        self.async_opened += 1
        self.parameters = {
            "hostname": hostname,
            "username": username,
            "password": password,
            "port": port,
            "platform": platform,
            "extras": extras,
            "configuration": configuration,
        }
        await asyncio.sleep(0)

    async def aclose(self) -> None:
        await asyncio.sleep(0)
        self.async_closed += 1


class MutableCapabilitiesPlugin(DualPlugin):
    instances: ClassVar[list[Any]] = []

    def __init__(self) -> None:
        super().__init__()
        self.reported: frozenset[ConnectionCapability] = frozenset({"sync", "asyncio"})

    def get_capabilities(self) -> frozenset[ConnectionCapability]:
        return self.reported


class FailingSyncClosePlugin(SyncPlugin):
    instances: ClassVar[list[Any]] = []

    def close(self) -> None:
        self.closed += 1
        raise RuntimeError("sync close failed")


@pytest.fixture(autouse=True)
def isolated_connection_registries() -> Iterator[None]:
    legacy_available = ConnectionPluginRegister.available
    capability_available = CapabilityConnectionPluginRegister.available
    legacy = legacy_available.copy()
    capability = capability_available.copy()
    legacy_available.clear()
    capability_available.clear()
    for plugin in (
        LegacyPlugin,
        SyncPlugin,
        AsyncPlugin,
        DualPlugin,
        MutableCapabilitiesPlugin,
        FailingSyncClosePlugin,
    ):
        plugin.instances.clear()
    AsyncPlugin.open_gate = None
    AsyncPlugin.open_started = None
    AsyncPlugin.close_gate = None
    AsyncPlugin.close_started = None
    AsyncPlugin.fail_open = False
    AsyncPlugin.fail_close = False
    yield
    legacy_available.clear()
    legacy_available.update(legacy)
    capability_available.clear()
    capability_available.update(capability)
    ConnectionPluginRegister.available = legacy_available
    CapabilityConnectionPluginRegister.available = capability_available


def configured_host() -> tuple[Host, Config]:
    config = Config()
    defaults = Defaults(
        username="default-user",
        connection_options={"transport": ConnectionOptions(port=22, extras={"source": "defaults"})},
    )
    host = Host(
        "host",
        hostname="host.example",
        platform="linux",
        connection_options={"transport": ConnectionOptions(username="host-user")},
        defaults=defaults,
    )
    return host, config


def test_legacy_and_capability_sync_opening_preserve_public_types_and_parameters() -> None:
    host, config = configured_host()
    ConnectionPluginRegister.register("legacy", LegacyPlugin)
    CapabilityConnectionPluginRegister.register("transport", SyncPlugin)

    legacy: ConnectionPlugin = host.open_connection("legacy", config)
    sync: ConnectionPlugin = host.open_connection("transport", config)

    assert isinstance(sync, SyncPlugin)
    assert host.connections == {"legacy": legacy, "transport": sync}
    assert host.get_connection("transport", config) is sync.connection
    assert sync.opened == 1
    assert sync.parameters == {
        "hostname": "host.example",
        "username": "host-user",
        "password": None,
        "port": 22,
        "platform": "linux",
        "extras": {"source": "defaults"},
        "configuration": config,
    }


def test_open_parameter_overrides_and_default_to_host_attributes_false() -> None:
    host, config = configured_host()
    CapabilityConnectionPluginRegister.register("transport", SyncPlugin)

    plugin = host.open_connection(
        "transport",
        config,
        hostname="explicit.example",
        port=443,
        extras={"source": "explicit"},
        default_to_host_attributes=False,
    )

    assert isinstance(plugin, SyncPlugin)
    assert plugin.parameters == {
        "hostname": "explicit.example",
        "username": None,
        "password": None,
        "port": 443,
        "platform": None,
        "extras": {"source": "explicit"},
        "configuration": config,
    }


def test_async_open_uses_parameters_once_and_keeps_async_only_cache_private() -> None:
    async def scenario() -> None:
        host, config = configured_host()
        CapabilityConnectionPluginRegister.register("transport", AsyncPlugin)

        first = await host.aget_connection("transport", config)
        second = await host.aget_connection("transport", config)

        plugin = AsyncPlugin.instances[0]
        assert first is second is plugin.connection
        assert plugin.opened == 1
        assert plugin.parameters["username"] == "host-user"
        assert host.connections == {}
        assert host._async_connections == {"transport": plugin}

    asyncio.run(scenario())


@pytest.mark.parametrize("async_first", [False, True])
def test_dual_connection_is_reused_across_modes_and_stays_public(async_first: bool) -> None:
    async def scenario() -> None:
        host = Host("host")
        config = Config()
        CapabilityConnectionPluginRegister.register("dual", DualPlugin)

        opened_plugin: ConnectionPlugin | AsyncCapabilityConnectionPlugin
        if async_first:
            opened_plugin = await host.aopen_connection("dual", config)
            transport = host.get_connection("dual", config)
        else:
            opened_plugin = host.open_connection("dual", config)
            transport = await host.aget_connection("dual", config)

        assert isinstance(opened_plugin, DualPlugin)
        assert transport is opened_plugin.connection
        assert opened_plugin.opened + opened_plugin.async_opened == 1
        assert host.connections == {"dual": opened_plugin}
        assert host._async_connections == {}

    asyncio.run(scenario())


def test_mode_checks_apply_before_uncached_and_cached_returns() -> None:
    async def scenario() -> None:
        config = Config()
        CapabilityConnectionPluginRegister.register("sync", SyncPlugin)
        CapabilityConnectionPluginRegister.register("async", AsyncPlugin)

        sync_host = Host("sync-host")
        with pytest.raises(ConnectionPluginNotAsyncError):
            await sync_host.aget_connection("sync", config)
        assert SyncPlugin.instances[0].opened == 0
        sync_host.get_connection("sync", config)
        with pytest.raises(ConnectionPluginNotAsyncError):
            await sync_host.aget_connection("sync", config)
        assert "sync" in sync_host.connections

        async_host = Host("async-host")
        with pytest.raises(ConnectionPluginNotSyncError):
            async_host.get_connection("async", config)
        assert AsyncPlugin.instances[0].opened == 0
        await async_host.aget_connection("async", config)
        with pytest.raises(ConnectionPluginNotSyncError):
            async_host.get_connection("async", config)
        assert "async" in async_host._async_connections

    asyncio.run(scenario())


def test_legacy_async_extensions_do_not_enable_async_mode() -> None:
    async def scenario() -> None:
        host = Host("host")
        ConnectionPluginRegister.register("legacy", LegacyPlugin)

        with pytest.raises(ConnectionPluginNotAsyncError):
            await host.aget_connection("legacy", Config())

        assert LegacyPlugin.instances == []

    asyncio.run(scenario())


def test_pending_open_rejects_get_and_both_opening_paths() -> None:
    async def scenario() -> None:
        host = Host("host")
        config = Config()
        gate = asyncio.Event()
        started = asyncio.Event()
        AsyncPlugin.open_gate = gate
        AsyncPlugin.open_started = started
        CapabilityConnectionPluginRegister.register("async", AsyncPlugin)
        opening = asyncio.create_task(host.aopen_connection("async", config))
        await started.wait()

        with pytest.raises(ConnectionAlreadyOpen):
            await host.aget_connection("async", config)
        with pytest.raises(ConnectionAlreadyOpen):
            await host.aopen_connection("async", config)
        with pytest.raises(ConnectionAlreadyOpen):
            host.open_connection("async", config)
        with pytest.raises(ConnectionAlreadyOpen):
            host.get_connection("async", config)

        gate.set()
        await opening
        assert "async" not in host._opening

    asyncio.run(scenario())


@pytest.mark.parametrize("cancel", [False, True])
def test_failed_or_cancelled_async_open_clears_reservation_without_publishing(
    cancel: bool,
) -> None:
    async def scenario() -> None:
        host = Host("host")
        gate = asyncio.Event()
        started = asyncio.Event()
        AsyncPlugin.open_gate = gate
        AsyncPlugin.open_started = started
        AsyncPlugin.fail_open = not cancel
        CapabilityConnectionPluginRegister.register("async", AsyncPlugin)
        opening = asyncio.create_task(host.aopen_connection("async", Config()))
        await started.wait()

        if cancel:
            opening.cancel()
            with pytest.raises(asyncio.CancelledError):
                await opening
            assert AsyncPlugin.instances[0].open_cancelled == 1
        else:
            gate.set()
            with pytest.raises(RuntimeError, match="open failed"):
                await opening

        assert host.connections == {}
        assert host._async_connections == {}
        assert host._capability_connections == {}
        assert host._opening == set()

    asyncio.run(scenario())


def test_cancelled_async_open_releases_plugin_partial_resource() -> None:
    class PartialResourcePlugin(AsyncPlugin):
        instances: ClassVar[list[Any]] = []

        def __init__(self) -> None:
            super().__init__()
            self.partial_resource: object | None = None
            self.released = 0

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
            self.partial_resource = object()
            try:
                await super().aopen(
                    hostname,
                    username,
                    password,
                    port,
                    platform,
                    extras,
                    configuration,
                )
            except asyncio.CancelledError:
                self.partial_resource = None
                self.released += 1
                raise

    async def scenario() -> None:
        host = Host("host")
        gate = asyncio.Event()
        started = asyncio.Event()
        PartialResourcePlugin.open_gate = gate
        PartialResourcePlugin.open_started = started
        CapabilityConnectionPluginRegister.register("partial", PartialResourcePlugin)
        opening = asyncio.create_task(host.aopen_connection("partial", Config()))
        await started.wait()
        plugin = PartialResourcePlugin.instances[0]
        assert plugin.partial_resource is not None

        opening.cancel()
        with pytest.raises(asyncio.CancelledError):
            await opening

        assert plugin.partial_resource is None
        assert plugin.released == 1
        assert host._opening == set()
        assert host.connections == {}
        assert host._async_connections == {}
        assert host._capability_connections == {}

    asyncio.run(scenario())


def test_cached_provenance_survives_deregistration_replacement_and_reporting_change() -> None:
    async def scenario() -> None:
        host = Host("host")
        config = Config()
        CapabilityConnectionPluginRegister.register("mutable", MutableCapabilitiesPlugin)
        transport = host.get_connection("mutable", config)
        plugin = MutableCapabilitiesPlugin.instances[0]
        plugin.reported = frozenset({"sync"})
        CapabilityConnectionPluginRegister.deregister("mutable")

        assert await host.aget_connection("mutable", config) is transport

        CapabilityConnectionPluginRegister.register("mutable", AsyncPlugin)
        assert host.get_connection("mutable", config) is transport
        assert await host.aget_connection("mutable", config) is transport
        assert len(MutableCapabilitiesPlugin.instances) == 1
        assert AsyncPlugin.instances == []

    asyncio.run(scenario())


def test_ambiguity_is_checked_on_every_cached_and_uncached_lookup() -> None:
    async def scenario() -> None:
        host = Host("host")
        config = Config()
        CapabilityConnectionPluginRegister.register("dual", DualPlugin)
        host.get_connection("dual", config)
        ConnectionPluginRegister.register("dual", LegacyPlugin)

        operations: tuple[Coroutine[Any, Any, Any], ...] = (
            host.aget_connection("dual", config),
            host.aopen_connection("dual", config),
        )
        with pytest.raises(ConnectionPluginAmbiguousError):
            host.get_connection("dual", config)
        with pytest.raises(ConnectionPluginAmbiguousError):
            host.open_connection("dual", config)
        for operation in operations:
            with pytest.raises(ConnectionPluginAmbiguousError):
                await operation

        await host.aclose_connection("dual")
        assert DualPlugin.instances[0].async_closed == 1

    asyncio.run(scenario())


def test_public_cache_replacement_is_treated_as_legacy_by_identity() -> None:
    async def scenario() -> None:
        host = Host("host")
        config = Config()
        CapabilityConnectionPluginRegister.register("dual", DualPlugin)
        original = host.open_connection("dual", config)
        replacement = LegacyPlugin()
        replacement.open(None, None, None, None, None)
        host.connections["dual"] = replacement

        assert isinstance(original, DualPlugin)
        assert host.get_connection("dual", config) is replacement.connection
        with pytest.raises(ConnectionPluginNotAsyncError):
            await host.aget_connection("dual", config)
        host.close_connection("dual")

        assert replacement.closed == 1
        assert original.closed == 0
        assert "dual" not in host._capability_connections

    asyncio.run(scenario())


def test_conflicting_public_and_private_entries_raise_contract_error() -> None:
    async def scenario() -> None:
        host = Host("host")
        config = Config()
        CapabilityConnectionPluginRegister.register("async", AsyncPlugin)
        await host.aget_connection("async", config)
        host.connections["async"] = LegacyPlugin()

        with pytest.raises(ConnectionPluginContractError):
            host.get_connection("async", config)
        with pytest.raises(ConnectionPluginContractError):
            await host.aget_connection("async", config)
        with pytest.raises(ConnectionPluginContractError):
            host.close_connection("async")
        with pytest.raises(ConnectionPluginContractError):
            await host.aclose_connection("async")

    asyncio.run(scenario())


def test_filtered_inventory_shares_host_connection_state() -> None:
    host = Host("host", data={"site": "a"})
    inventory = Inventory(Hosts({"host": host}), Groups(), Defaults())
    ConnectionPluginRegister.register("legacy", LegacyPlugin)

    filtered_host = inventory.filter(site="a").hosts["host"]
    filtered_host.get_connection("legacy", Config())

    assert filtered_host is host
    assert inventory.hosts["host"].connections == filtered_host.connections


def test_empty_host_copy_pickle_and_inventory_serialization_are_unchanged() -> None:
    host = Host("host", hostname="host.example", data={"site": "a"})
    expected_dict = host.dict()
    expected_schema = Host.schema()

    copied = copy.copy(host)
    restored = pickle.loads(pickle.dumps(host))  # noqa: S301 - data is created in this test.

    for candidate in (copied, restored):
        assert candidate.dict() == expected_dict
        assert candidate.connections == {}
        assert candidate._async_connections == {}
        assert candidate._capability_connections == {}
        assert candidate._opening == set()
    assert host.dict() == expected_dict
    assert Host.schema() == expected_schema


def test_capability_connection_state_is_immutable() -> None:
    host = Host("host")
    CapabilityConnectionPluginRegister.register("sync", SyncPlugin)
    host.get_connection("sync", Config())

    state = host._capability_connections["sync"]
    attribute = "capabilities"
    with pytest.raises(AttributeError):
        setattr(state, attribute, frozenset({"asyncio"}))


def test_sync_close_removes_instance_and_metadata_even_when_close_fails() -> None:
    host = Host("host")
    CapabilityConnectionPluginRegister.register("failing", FailingSyncClosePlugin)
    host.get_connection("failing", Config())

    with pytest.raises(RuntimeError, match="sync close failed"):
        host.close_connection("failing")

    assert "failing" not in host.connections
    assert "failing" not in host._capability_connections
    with pytest.raises(ConnectionNotOpen):
        host.close_connection("failing")


def test_async_close_failure_and_cancellation_retain_state_for_retry() -> None:
    async def scenario() -> None:
        host = Host("host")
        CapabilityConnectionPluginRegister.register("async", AsyncPlugin)
        await host.aget_connection("async", Config())
        plugin = AsyncPlugin.instances[0]

        AsyncPlugin.fail_close = True
        with pytest.raises(RuntimeError, match="close failed"):
            await host.aclose_connection("async")
        assert host._async_connections["async"] is plugin

        AsyncPlugin.fail_close = False
        close_started = asyncio.Event()
        close_gate = asyncio.Event()
        AsyncPlugin.close_started = close_started
        AsyncPlugin.close_gate = close_gate
        close = asyncio.create_task(host.aclose_connection("async"))
        await close_started.wait()
        close.cancel()
        with pytest.raises(asyncio.CancelledError):
            await close
        assert host._async_connections["async"] is plugin
        assert plugin.close_cancelled == 1

        AsyncPlugin.close_started = None
        AsyncPlugin.close_gate = None
        await host.aclose_connection("async")
        assert "async" not in host._async_connections
        assert "async" not in host._capability_connections

    asyncio.run(scenario())


def test_async_bulk_cleanup_closes_both_stores_and_prefers_dual_async_close() -> None:
    async def scenario() -> None:
        host = Host("host")
        config = Config()
        ConnectionPluginRegister.register("legacy", LegacyPlugin)
        CapabilityConnectionPluginRegister.register("sync", SyncPlugin)
        CapabilityConnectionPluginRegister.register("async", AsyncPlugin)
        CapabilityConnectionPluginRegister.register("dual", DualPlugin)
        host.get_connection("legacy", config)
        host.get_connection("sync", config)
        await host.aget_connection("async", config)
        host.get_connection("dual", config)

        await host.aclose_connections()

        assert LegacyPlugin.instances[0].closed == 1
        assert SyncPlugin.instances[0].closed == 1
        assert AsyncPlugin.instances[0].closed == 1
        assert DualPlugin.instances[0].async_closed == 1
        assert DualPlugin.instances[0].closed == 0
        assert host.connections == {}
        assert host._async_connections == {}
        assert host._capability_connections == {}

    asyncio.run(scenario())


def test_cancelled_async_close_retry_preserves_replacement_and_clears_old_metadata() -> None:
    class ReplacingDual(DualPlugin):
        instances: ClassVar[list[Any]] = []

        def __init__(self) -> None:
            super().__init__()
            self.close_attempts = 0
            self.close_cancelled = 0

        async def aclose(self) -> None:
            self.close_attempts += 1
            if self.close_attempts == 1:
                close_started.set()
                try:
                    await close_gate.wait()
                except asyncio.CancelledError:
                    self.close_cancelled += 1
                    raise
            host.connections["dual"] = replacement
            await asyncio.sleep(0)
            self.async_closed += 1

    async def scenario() -> None:
        CapabilityConnectionPluginRegister.register("dual", ReplacingDual)
        await host.aget_connection("dual", Config())
        plugin: ReplacingDual = ReplacingDual.instances[0]

        closing = asyncio.create_task(host.aclose_connection("dual"))
        await close_started.wait()
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing

        assert host.connections["dual"] is plugin
        assert host._capability_connections["dual"].plugin is plugin
        assert plugin.close_cancelled == 1

        await host.aclose_connection("dual")

        assert host.connections["dual"] is replacement
        assert "dual" not in host._capability_connections
        assert plugin.async_closed == 1
        assert host.get_connection("dual", Config()) is replacement.connection

    host = Host("host")
    replacement = LegacyPlugin()
    close_started = asyncio.Event()
    close_gate = asyncio.Event()
    asyncio.run(scenario())


def test_sync_bulk_cleanup_is_fail_fast_and_rejects_async_only_entries() -> None:
    async def prepare() -> Host:
        host = Host("host")
        CapabilityConnectionPluginRegister.register("failing", FailingSyncClosePlugin)
        CapabilityConnectionPluginRegister.register("later", SyncPlugin)
        CapabilityConnectionPluginRegister.register("async", AsyncPlugin)
        host.get_connection("failing", Config())
        host.get_connection("later", Config())
        await host.aget_connection("async", Config())
        return host

    host = asyncio.run(prepare())
    with pytest.raises(RuntimeError, match="sync close failed"):
        host.close_connections()

    assert "failing" not in host.connections
    assert "later" in host.connections
    assert "async" in host._async_connections

    host.close_connection("later")
    with pytest.raises(ConnectionPluginNotSyncError):
        host.close_connections()
    assert "async" in host._async_connections


def test_async_bulk_cleanup_attempts_all_and_raises_first_ordinary_error() -> None:
    class FirstFailure(AsyncPlugin):
        instances: ClassVar[list[Any]] = []
        fail_close: ClassVar[bool] = True

    class SecondFailure(AsyncPlugin):
        instances: ClassVar[list[Any]] = []
        fail_close: ClassVar[bool] = True

    async def scenario() -> None:
        host = Host("host")
        CapabilityConnectionPluginRegister.register("first", FirstFailure)
        CapabilityConnectionPluginRegister.register("second", SecondFailure)
        CapabilityConnectionPluginRegister.register("sync", SyncPlugin)
        await host.aget_connection("first", Config())
        await host.aget_connection("second", Config())
        host.get_connection("sync", Config())

        with pytest.raises(RuntimeError, match="close failed"):
            await host.aclose_connections()

        assert FirstFailure.instances[0].closed == 0
        assert SecondFailure.instances[0].closed == 0
        assert SyncPlugin.instances[0].closed == 1
        assert set(host._async_connections) == {"first", "second"}
        assert host.connections == {}

    asyncio.run(scenario())


def test_async_bulk_cleanup_propagates_cancellation_without_later_attempts() -> None:
    class CancellingPlugin(AsyncPlugin):
        instances: ClassVar[list[Any]] = []

        async def aclose(self) -> None:
            raise asyncio.CancelledError

    async def scenario() -> None:
        host = Host("host")
        CapabilityConnectionPluginRegister.register("cancel", CancellingPlugin)
        CapabilityConnectionPluginRegister.register("later", AsyncPlugin)
        await host.aget_connection("cancel", Config())
        await host.aget_connection("later", Config())

        with pytest.raises(asyncio.CancelledError):
            await host.aclose_connections()

        assert "cancel" in host._async_connections
        assert "later" in host._async_connections
        assert AsyncPlugin.instances[0].closed == 0

    asyncio.run(scenario())
