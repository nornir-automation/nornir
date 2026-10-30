from __future__ import annotations

import asyncio
import threading
import traceback
from importlib import metadata
from typing import TYPE_CHECKING, Any

import pytest

from nornir import AInitNornir, InitNornir
from nornir.core.exceptions import (
    InventoryPluginAmbiguousError,
    InventoryPluginContractError,
    InventoryPluginNotSyncError,
    PluginNotRegistered,
)
from nornir.core.plugins.inventory import (
    CAPABILITY_INVENTORY_PLUGIN_PATH,
    CapabilityInventoryPluginRegister,
    InventoryCapability,
    InventoryPluginRegister,
)
from nornir.core.plugins.runners import RunnersPluginRegister
from tests.core.inventory_plugins import (
    RECORDER,
    AsyncCapabilityPlugin,
    DualCapabilityPlugin,
    LegacyPlugin,
    SyncCapabilityPlugin,
    build_test_inventory,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from nornir.core import Nornir
    from nornir.core.inventory import Inventory

pytestmark = pytest.mark.usefixtures("isolated_inventory_registries")


def ainit(**kwargs: Any) -> Nornir:
    return asyncio.run(AInitNornir(**kwargs))


ENTRY_POINTS = [pytest.param(InitNornir, id="sync"), pytest.param(ainit, id="async")]


class EmptyDeclarationPlugin(SyncCapabilityPlugin):
    def get_capabilities(self) -> frozenset[InventoryCapability]:
        RECORDER.record("get_capabilities")
        return frozenset()


class WaitingAsyncPlugin:
    """Asyncio plugin whose ``aload`` waits for an event set by another coroutine."""

    def __init__(self, ready: asyncio.Event, started: asyncio.Event | None = None) -> None:
        self.ready = ready
        self.started = started or asyncio.Event()

    def get_capabilities(self) -> frozenset[InventoryCapability]:
        return frozenset({"asyncio"})

    async def aload(self) -> Inventory:
        self.started.set()
        try:
            await self.ready.wait()
        finally:
            RECORDER.record("aload-finished")
        return build_test_inventory()


class FailingAsyncPlugin(AsyncCapabilityPlugin):
    async def aload(self) -> Inventory:
        await asyncio.sleep(0)
        msg = "inventory API unavailable"
        raise ValueError(msg)


class FakeEntryPoint:
    def __init__(self, name: str, plugin: type[Any]) -> None:
        self.name = name
        self.plugin = plugin

    def load(self) -> type[Any]:
        return self.plugin


def test_dual_plugin_uses_the_method_matching_the_entry_point() -> None:
    CapabilityInventoryPluginRegister.register("dual", DualCapabilityPlugin)

    ainit(inventory={"plugin": "dual"})
    assert RECORDER.names() == ["init", "get_capabilities", "aload"]

    RECORDER.reset()
    InitNornir(inventory={"plugin": "dual"})
    assert RECORDER.names() == ["init", "get_capabilities", "load"]


def test_asyncio_only_plugin() -> None:
    CapabilityInventoryPluginRegister.register("api", AsyncCapabilityPlugin)

    nr = ainit(inventory={"plugin": "api"})
    assert list(nr.inventory.hosts) == ["h1", "h2", "h3"]
    assert RECORDER.names() == ["init", "get_capabilities", "aload"]

    RECORDER.reset()
    with pytest.raises(InventoryPluginNotSyncError, match=r"AInitNornir") as exc_info:
        InitNornir(inventory={"plugin": "api"})
    assert exc_info.value.plugin_name == "api"
    assert "load" not in RECORDER.names()
    assert "aload" not in RECORDER.names()


def test_sync_only_capability_plugin() -> None:
    CapabilityInventoryPluginRegister.register("sync-cap", SyncCapabilityPlugin)

    async def scenario() -> int:
        await AInitNornir(inventory={"plugin": "sync-cap"})
        return threading.get_ident()

    loop_thread = asyncio.run(scenario())
    assert RECORDER.names() == ["init", "get_capabilities", "load"]
    assert RECORDER.threads["load"] != loop_thread

    RECORDER.reset()
    InitNornir(inventory={"plugin": "sync-cap"})
    assert RECORDER.names() == ["init", "get_capabilities", "load"]


def test_aload_shares_the_loop_with_other_work() -> None:
    CapabilityInventoryPluginRegister.register("waiting", WaitingAsyncPlugin)

    async def scenario() -> Nornir:
        ready = asyncio.Event()

        async def release() -> None:
            await asyncio.sleep(0)
            ready.set()

        releaser = asyncio.create_task(release())
        nr = await asyncio.wait_for(
            AInitNornir(inventory={"plugin": "waiting", "options": {"ready": ready}}), timeout=5
        )
        await releaser
        return nr

    assert list(asyncio.run(scenario()).inventory.hosts) == ["h1", "h2", "h3"]


@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_name_in_both_registries_is_ambiguous(init: Callable[..., Nornir]) -> None:
    InventoryPluginRegister.register("both", LegacyPlugin)
    CapabilityInventoryPluginRegister.register("both", DualCapabilityPlugin)

    with pytest.raises(InventoryPluginAmbiguousError) as exc_info:
        init(inventory={"plugin": "both"})

    assert exc_info.value.plugin_name == "both"
    assert RECORDER.names() == []


@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_name_used_by_a_legacy_runner_is_ambiguous(init: Callable[..., Nornir]) -> None:
    # The legacy registers share one dictionary, so a registered runner name collides.
    RunnersPluginRegister.auto_register()
    CapabilityInventoryPluginRegister.register("threaded", DualCapabilityPlugin)

    with pytest.raises(InventoryPluginAmbiguousError, match="both") as exc_info:
        init(inventory={"plugin": "threaded"})

    assert "legacy" in str(exc_info.value)
    assert "capability-aware" in str(exc_info.value)


@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_invalid_declaration_is_a_contract_error(init: Callable[..., Nornir]) -> None:
    CapabilityInventoryPluginRegister.register("empty-declaration", EmptyDeclarationPlugin)

    with pytest.raises(InventoryPluginContractError):
        init(inventory={"plugin": "empty-declaration"})

    assert RECORDER.names() == ["init", "get_capabilities"]


@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_unregistered_name(init: Callable[..., Nornir]) -> None:
    with pytest.raises(PluginNotRegistered):
        init(inventory={"plugin": "nowhere"})


def test_one_entry_point_serves_both_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    original = metadata.entry_points

    def entry_points(*, group: str) -> Any:
        if group == CAPABILITY_INVENTORY_PLUGIN_PATH:
            return [FakeEntryPoint("from-entry-point", DualCapabilityPlugin)]
        return original(group=group)

    monkeypatch.setattr(metadata, "entry_points", entry_points)

    ainit(inventory={"plugin": "from-entry-point"})
    InitNornir(inventory={"plugin": "from-entry-point"})

    assert [name for name in RECORDER.names() if name in {"load", "aload"}] == ["aload", "load"]


def test_cancellation_reaches_aload() -> None:
    CapabilityInventoryPluginRegister.register("waiting", WaitingAsyncPlugin)

    async def scenario() -> None:
        never = asyncio.Event()
        started = asyncio.Event()
        init = asyncio.create_task(
            AInitNornir(
                inventory={"plugin": "waiting", "options": {"ready": never, "started": started}}
            )
        )
        await asyncio.wait_for(started.wait(), timeout=5)
        init.cancel()
        with pytest.raises(asyncio.CancelledError):
            await init

    asyncio.run(scenario())

    assert RECORDER.names() == ["aload-finished"]


def test_aload_error_propagates_with_plugin_frame() -> None:
    CapabilityInventoryPluginRegister.register("failing", FailingAsyncPlugin)

    with pytest.raises(ValueError, match="inventory API unavailable") as exc_info:
        ainit(inventory={"plugin": "failing"})

    frames = traceback.extract_tb(exc_info.value.__traceback__)
    assert frames[-1].name == "aload"
    assert frames[-1].filename == __file__
