from __future__ import annotations

import asyncio
import inspect
import threading
import time
import traceback
from typing import TYPE_CHECKING, Any

import pytest

import nornir
from nornir import AInitNornir, InitNornir
from nornir.core.inventory import Defaults, Groups, Hosts, Inventory
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir.plugins.runners import AsyncioRunner, SerialRunner, ThreadedRunner
from tests.core.inventory_plugins import (
    RECORDER,
    BlockingLegacyPlugin,
    LegacyPlugin,
    build_test_inventory,
)
from tests.core.test_InitNornir import dir_path

if TYPE_CHECKING:
    from nornir.core import Nornir

pytestmark = pytest.mark.usefixtures("isolated_inventory_registries")

INVENTORY_DATA = {
    "host_file": "tests/inventory_data/hosts.yaml",
    "group_file": "tests/inventory_data/groups.yaml",
}


class AsyncioRunInLoadPlugin:
    """Synchronous plugin that drives its own event loop, as some plugins do today."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    def load(self) -> Inventory:
        async def fetch() -> Inventory:
            await asyncio.sleep(0)
            return build_test_inventory()

        return asyncio.run(fetch())


class EmptyPlugin:
    def __init__(self, **kwargs: Any) -> None:
        pass

    def load(self) -> Inventory:
        return Inventory(hosts=Hosts(), groups=Groups(), defaults=Defaults())


class FailingPlugin:
    def __init__(self, **kwargs: Any) -> None:
        pass

    def load(self) -> Inventory:
        msg = "inventory source unavailable"
        raise ValueError(msg)


def ainit(**kwargs: Any) -> Nornir:
    return asyncio.run(AInitNornir(**kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({}, id="bare"),
        pytest.param({"config_file": str(dir_path / "a_config.yaml")}, id="config-file"),
        pytest.param(
            {"inventory": {"plugin": "SimpleInventory", "options": INVENTORY_DATA}},
            id="simple-inventory",
        ),
        pytest.param({"inventory": {"plugin": "inventory-test"}}, id="inventory-test"),
        pytest.param(
            {
                "config_file": str(dir_path / "a_config.yaml"),
                "inventory": {
                    "plugin": "inventory-test",
                    "transform_function": "transform_func",
                    "options": INVENTORY_DATA,
                },
            },
            id="transform",
        ),
        pytest.param(
            {
                "config_file": str(dir_path / "a_config.yaml"),
                "inventory": {
                    "plugin": "inventory-test",
                    "transform_function": "transform_func_with_options",
                    "transform_function_options": {"a": 1},
                    "options": INVENTORY_DATA,
                },
            },
            id="transform-with-options",
        ),
    ],
)
def test_same_inventory_as_init_nornir(
    kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    if not kwargs:
        monkeypatch.chdir("tests/inventory_data/")

    expected = InitNornir(**kwargs).inventory.dict()

    assert ainit(**kwargs).inventory.dict() == expected


def test_same_error_for_bad_transform_options() -> None:
    kwargs: dict[str, Any] = {
        "inventory": {
            "plugin": "inventory-test",
            "transform_function": "transform_func_with_options",
            "transform_function_options": {"a": 1, "b": 0},
        },
    }

    with pytest.raises(TypeError):
        InitNornir(**kwargs)
    with pytest.raises(TypeError):
        ainit(**kwargs)


def test_sync_load_does_not_block_the_loop() -> None:
    InventoryPluginRegister.register("blocking", BlockingLegacyPlugin)

    async def scenario() -> Nornir:
        event = threading.Event()

        async def release() -> None:
            # Only runs if the loop is free while load() waits for the event.
            await asyncio.sleep(0)
            event.set()

        releaser = asyncio.create_task(release())
        nr = await asyncio.wait_for(
            AInitNornir(inventory={"plugin": "blocking", "options": {"event": event}}),
            timeout=10,
        )
        await releaser
        return nr

    nr = asyncio.run(scenario())

    assert list(nr.inventory.hosts) == ["h1", "h2", "h3"]


def test_sync_load_runs_in_a_worker_thread() -> None:
    InventoryPluginRegister.register("legacy", LegacyPlugin)

    async def scenario() -> int:
        await AInitNornir(inventory={"plugin": "legacy"})
        return threading.get_ident()

    loop_thread = asyncio.run(scenario())

    assert RECORDER.names() == ["init", "load"]
    assert RECORDER.threads["load"] != loop_thread


def test_plugin_running_its_own_event_loop_works() -> None:
    InventoryPluginRegister.register("own-loop", AsyncioRunInLoadPlugin)

    nr = ainit(inventory={"plugin": "own-loop"})

    assert list(nr.inventory.hosts) == ["h1", "h2", "h3"]


def test_same_signature_as_init_nornir() -> None:
    expected = inspect.signature(InitNornir).parameters
    actual = inspect.signature(AInitNornir).parameters

    assert list(actual) == list(expected)
    for name, parameter in expected.items():
        assert actual[name].kind is parameter.kind
        assert actual[name].default == parameter.default


def test_same_configuration_as_init_nornir() -> None:
    kwargs: dict[str, Any] = {
        "dry_run": True,
        "inventory": {"plugin": "inventory-test"},
        "core": {"raise_on_error": True},
        "runner": {"plugin": "serial"},
        "logging": {"enabled": False},
        "user_defined": {"site": "par1"},
    }

    expected = InitNornir(**kwargs)
    actual = ainit(**kwargs)

    assert actual.data.dry_run is expected.data.dry_run is True
    assert actual.config.dict() == expected.config.dict()


def test_empty_inventory() -> None:
    InventoryPluginRegister.register("empty", EmptyPlugin)

    assert len(ainit(inventory={"plugin": "empty"}).inventory.hosts) == 0


def test_load_error_propagates_with_plugin_frame() -> None:
    InventoryPluginRegister.register("failing", FailingPlugin)

    with pytest.raises(ValueError, match="inventory source unavailable") as exc_info:
        ainit(inventory={"plugin": "failing"})

    frames = traceback.extract_tb(exc_info.value.__traceback__)
    assert frames[-1].name == "load"
    assert frames[-1].filename == __file__


def test_cancellation_does_not_wait_for_sync_load() -> None:
    InventoryPluginRegister.register("blocking", BlockingLegacyPlugin)

    async def scenario() -> float:
        event = threading.Event()
        started = threading.Event()
        init = asyncio.create_task(
            AInitNornir(
                inventory={"plugin": "blocking", "options": {"event": event, "started": started}}
            )
        )

        assert await asyncio.to_thread(started.wait, 5)
        init.cancel()
        start = time.monotonic()
        with pytest.raises(asyncio.CancelledError):
            await init
        elapsed = time.monotonic() - start
        # asyncio.run() waits for executor threads on exit, so release load() here.
        event.set()
        return elapsed

    assert asyncio.run(scenario()) < 1


def test_exported_from_nornir() -> None:
    assert "AInitNornir" in nornir.__all__
    assert nornir.AInitNornir is AInitNornir


@pytest.mark.parametrize(
    ("runner", "runner_type"),
    [("threaded", ThreadedRunner), ("serial", SerialRunner), ("asyncio", AsyncioRunner)],
)
def test_independent_of_the_runner(runner: str, runner_type: type[Any]) -> None:
    nr = ainit(inventory={"plugin": "inventory-test"}, runner={"plugin": runner})

    assert isinstance(nr.runner, runner_type)
