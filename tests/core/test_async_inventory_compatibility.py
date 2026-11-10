"""Configurations that load on develop and must keep loading with async inventory support."""

from __future__ import annotations

import asyncio
import signal
from importlib import metadata
from typing import TYPE_CHECKING, Any

import pytest

from nornir import AInitNornir, InitNornir
from nornir.core.plugins.inventory import (
    ASYNC_TRANSFORM_FUNCTION_PLUGIN_PATH,
    CAPABILITY_INVENTORY_PLUGIN_PATH,
    CapabilityInventoryPluginRegister,
    InventoryPluginRegister,
    TransformFunctionRegister,
)
from tests.core.inventory_plugins import (
    RECORDER,
    AsyncCapabilityPlugin,
    DualCapabilityPlugin,
    LegacyPlugin,
    SyncCapabilityPlugin,
    sync_transform,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from nornir.core import Nornir
    from nornir.core.inventory import Inventory

pytestmark = pytest.mark.usefixtures("isolated_inventory_registries")


def ainit(**kwargs: Any) -> Nornir:
    return asyncio.run(AInitNornir(**kwargs))


ENTRY_POINTS = [pytest.param(InitNornir, id="sync"), pytest.param(ainit, id="async")]


class TransformRegisteringPlugin(LegacyPlugin):
    """Legacy plugin that registers the transform function it is configured with."""

    def load(self) -> Inventory:
        TransformFunctionRegister.register("registered-by-plugin", sync_transform)
        return super().load()


class SignalHandlingPlugin(LegacyPlugin):
    """Legacy plugin that installs a signal handler, which only the main thread can do."""

    def load(self) -> Inventory:
        signal.signal(signal.SIGINT, signal.getsignal(signal.SIGINT) or signal.SIG_DFL)
        return super().load()


class FakeEntryPoint:
    def __init__(self, name: str, plugin: type[Any]) -> None:
        self.name = name
        self.plugin = plugin

    def load(self) -> type[Any]:
        return self.plugin


class BrokenEntryPoint:
    name = "broken"

    def load(self) -> type[Any]:
        msg = "No module named 'broken_plugin'"
        raise ImportError(msg)


def replace_entry_points(
    monkeypatch: pytest.MonkeyPatch, target_group: str, replacement: list[Any]
) -> None:
    original = metadata.entry_points

    def patched(*, group: str) -> Any:
        if group == target_group:
            return replacement
        return original(group=group)

    monkeypatch.setattr(metadata, "entry_points", patched)


@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_plugin_can_register_its_transform_function_while_loading(
    init: Callable[..., Nornir],
) -> None:
    # On develop the transform function is looked up after the plugin has loaded.
    InventoryPluginRegister.register("transform-registering", TransformRegisteringPlugin)

    nr = init(
        inventory={
            "plugin": "transform-registering",
            "transform_function": "registered-by-plugin",
            "transform_function_options": {"site": "lab"},
        }
    )

    assert {host.data["site"] for host in nr.inventory.hosts.values()} == {"lab"}


@pytest.mark.parametrize("init", ENTRY_POINTS)
@pytest.mark.parametrize(
    "group",
    [
        pytest.param(CAPABILITY_INVENTORY_PLUGIN_PATH, id="capability-inventory"),
        pytest.param(ASYNC_TRANSFORM_FUNCTION_PLUGIN_PATH, id="async-transform"),
    ],
)
def test_broken_entry_point_in_an_unused_group_does_not_stop_a_legacy_configuration(
    monkeypatch: pytest.MonkeyPatch, init: Callable[..., Nornir], group: str
) -> None:
    InventoryPluginRegister.register("legacy", LegacyPlugin)
    TransformFunctionRegister.register("legacy-transform", sync_transform)
    replace_entry_points(monkeypatch, group, [BrokenEntryPoint()])

    nr = init(inventory={"plugin": "legacy", "transform_function": "legacy-transform"})

    assert list(nr.inventory.hosts) == ["h1", "h2", "h3"]


@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_duplicate_capability_entry_points_do_not_stop_a_legacy_configuration(
    monkeypatch: pytest.MonkeyPatch, init: Callable[..., Nornir]
) -> None:
    InventoryPluginRegister.register("legacy", LegacyPlugin)
    replace_entry_points(
        monkeypatch,
        CAPABILITY_INVENTORY_PLUGIN_PATH,
        [
            FakeEntryPoint("published-twice", SyncCapabilityPlugin),
            FakeEntryPoint("published-twice", AsyncCapabilityPlugin),
        ],
    )

    nr = init(inventory={"plugin": "legacy"})

    assert list(nr.inventory.hosts) == ["h1", "h2", "h3"]


@pytest.mark.parametrize(
    ("init", "load_method"),
    [pytest.param(InitNornir, "load", id="sync"), pytest.param(ainit, "aload", id="async")],
)
def test_same_class_in_both_inventory_registries_is_not_ambiguous(
    init: Callable[..., Nornir], load_method: str
) -> None:
    # A plugin that adds aload keeps its legacy entry point for older Nornir releases.
    InventoryPluginRegister.register("upgraded", DualCapabilityPlugin)
    CapabilityInventoryPluginRegister.register("upgraded", DualCapabilityPlugin)

    nr = init(inventory={"plugin": "upgraded"})

    assert list(nr.inventory.hosts) == ["h1", "h2", "h3"]
    assert RECORDER.names() == ["init", "get_capabilities", load_method]


def test_legacy_plugin_that_needs_the_main_thread_loads_with_initnornir() -> None:
    InventoryPluginRegister.register("signal-handling", SignalHandlingPlugin)

    nr = InitNornir(inventory={"plugin": "signal-handling"})

    assert list(nr.inventory.hosts) == ["h1", "h2", "h3"]


def test_legacy_plugin_that_needs_the_main_thread_fails_with_ainitnornir() -> None:
    # AInitNornir loads legacy plugins in a worker thread; the documentation says so.
    InventoryPluginRegister.register("signal-handling", SignalHandlingPlugin)

    with pytest.raises(ValueError, match="main thread"):
        ainit(inventory={"plugin": "signal-handling"})
