from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any, cast

import pytest

from nornir import AInitNornir, InitNornir
from nornir.core.exceptions import (
    InventoryPluginAmbiguousError,
    PluginNotRegistered,
    TransformFunctionAmbiguousError,
    TransformFunctionNotSyncError,
)
from nornir.core.plugins.inventory import (
    AsyncTransformFunction,
    AsyncTransformFunctionRegister,
    CapabilityInventoryPluginRegister,
    InventoryPluginRegister,
    TransformFunctionRegister,
)
from tests.core.inventory_plugins import (
    HOST_NAMES,
    RECORDER,
    AsyncCapabilityPlugin,
    DualCapabilityPlugin,
    LegacyPlugin,
    async_transform,
    sync_transform,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from nornir.core import Nornir
    from nornir.core.inventory import Host, TransformFunction

pytestmark = pytest.mark.usefixtures("isolated_inventory_registries")


def ainit(**kwargs: Any) -> Nornir:
    return asyncio.run(AInitNornir(**kwargs))


ENTRY_POINTS = [pytest.param(InitNornir, id="sync"), pytest.param(ainit, id="async")]

SEQUENTIAL_EVENTS = [(event, name) for name in HOST_NAMES for event in ("start", "end")]


async def failing_on_third_host(host: Host, **kwargs: Any) -> None:
    await asyncio.sleep(0)
    if host.name == HOST_NAMES[2]:
        msg = f"secret store has no entry for {host.name}"
        raise KeyError(msg)


def transform_events() -> list[tuple[str, ...]]:
    return [event for event in RECORDER.events if event[0] in {"start", "end"}]


@pytest.fixture
def legacy_plugin() -> None:
    InventoryPluginRegister.register("legacy", LegacyPlugin)


@pytest.mark.usefixtures("legacy_plugin")
def test_async_transform_is_awaited_per_host_in_order() -> None:
    AsyncTransformFunctionRegister.register("enrich", async_transform)

    nr = ainit(
        inventory={
            "plugin": "legacy",
            "transform_function": "enrich",
            "transform_function_options": {"site": "par1"},
        }
    )

    assert transform_events() == SEQUENTIAL_EVENTS
    assert all(host.data == {"site": "par1"} for host in nr.inventory.hosts.values())


def test_async_transform_with_asyncio_plugin() -> None:
    CapabilityInventoryPluginRegister.register("api", AsyncCapabilityPlugin)
    AsyncTransformFunctionRegister.register("enrich", async_transform)

    ainit(inventory={"plugin": "api", "transform_function": "enrich"})

    assert RECORDER.names()[:3] == ["init", "get_capabilities", "aload"]
    assert transform_events() == SEQUENTIAL_EVENTS


@pytest.mark.parametrize(
    ("plugin_name", "plugin"),
    [("legacy", LegacyPlugin), ("api", AsyncCapabilityPlugin)],
)
def test_sync_transform_runs_in_a_worker_thread(plugin_name: str, plugin: type[Any]) -> None:
    if plugin is LegacyPlugin:
        InventoryPluginRegister.register(plugin_name, plugin)
    else:
        CapabilityInventoryPluginRegister.register(plugin_name, plugin)
    TransformFunctionRegister.register("tag", sync_transform)

    async def scenario() -> int:
        await AInitNornir(inventory={"plugin": plugin_name, "transform_function": "tag"})
        return threading.get_ident()

    loop_thread = asyncio.run(scenario())

    assert RECORDER.names().count("transform") == len(HOST_NAMES)
    assert RECORDER.threads["transform"] != loop_thread


@pytest.mark.usefixtures("legacy_plugin")
def test_init_nornir_refuses_async_transform_before_loading() -> None:
    AsyncTransformFunctionRegister.register("enrich", async_transform)

    with pytest.raises(TransformFunctionNotSyncError, match="AInitNornir") as exc_info:
        InitNornir(inventory={"plugin": "legacy", "transform_function": "enrich"})

    assert exc_info.value.transform_name == "enrich"
    assert RECORDER.names() == []


@pytest.mark.usefixtures("legacy_plugin")
def test_async_def_in_the_legacy_registry_is_treated_as_async() -> None:
    TransformFunctionRegister.register("enrich", cast("TransformFunction", async_transform))

    ainit(inventory={"plugin": "legacy", "transform_function": "enrich"})
    assert transform_events() == SEQUENTIAL_EVENTS

    RECORDER.reset()
    with pytest.raises(TransformFunctionNotSyncError):
        InitNornir(inventory={"plugin": "legacy", "transform_function": "enrich"})
    assert RECORDER.names() == []


@pytest.mark.usefixtures("legacy_plugin")
@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_plain_function_in_the_async_registry_runs_synchronously(
    init: Callable[..., Nornir],
) -> None:
    AsyncTransformFunctionRegister.register("tag", cast("AsyncTransformFunction", sync_transform))

    init(inventory={"plugin": "legacy", "transform_function": "tag"})

    assert RECORDER.names().count("transform") == len(HOST_NAMES)


@pytest.mark.usefixtures("legacy_plugin")
def test_async_transform_error_propagates() -> None:
    AsyncTransformFunctionRegister.register("failing", failing_on_third_host)

    with pytest.raises(KeyError, match="no entry for h3"):
        ainit(inventory={"plugin": "legacy", "transform_function": "failing"})


@pytest.mark.usefixtures("legacy_plugin")
@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_name_in_both_transform_registries_is_ambiguous(init: Callable[..., Nornir]) -> None:
    TransformFunctionRegister.register("both", sync_transform)
    AsyncTransformFunctionRegister.register("both", async_transform)

    with pytest.raises(TransformFunctionAmbiguousError) as exc_info:
        init(inventory={"plugin": "legacy", "transform_function": "both"})

    assert exc_info.value.transform_name == "both"
    assert RECORDER.names() == []


@pytest.mark.usefixtures("legacy_plugin")
@pytest.mark.parametrize("init", ENTRY_POINTS)
def test_unregistered_transform(init: Callable[..., Nornir]) -> None:
    with pytest.raises(PluginNotRegistered):
        init(inventory={"plugin": "legacy", "transform_function": "nowhere"})

    assert RECORDER.names() == []


def test_ambiguous_plugin_wins_over_async_transform() -> None:
    InventoryPluginRegister.register("both", LegacyPlugin)
    CapabilityInventoryPluginRegister.register("both", DualCapabilityPlugin)
    AsyncTransformFunctionRegister.register("enrich", async_transform)

    with pytest.raises(InventoryPluginAmbiguousError):
        InitNornir(inventory={"plugin": "both", "transform_function": "enrich"})
