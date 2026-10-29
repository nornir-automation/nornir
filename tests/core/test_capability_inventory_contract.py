from __future__ import annotations

import asyncio
from typing import Any

import pytest

from nornir.core.exceptions import InventoryPluginContractError
from nornir.core.inventory import Hosts, Inventory
from nornir.core.plugins.inventory import (
    AsyncTransformFunctionRegister,
    CapabilityInventoryPluginRegister,
    InventoryCapability,
    InventoryPluginRegister,
    TransformFunctionRegister,
    _validate_capability_inventory_plugin,  # noqa: PLC2701 - unit test of the private validator
)


class SyncOnly:
    def get_capabilities(self) -> frozenset[InventoryCapability]:
        return frozenset({"sync"})

    def load(self) -> Inventory:
        return Inventory(hosts=Hosts())


class AsyncOnly:
    def get_capabilities(self) -> frozenset[InventoryCapability]:
        return frozenset({"asyncio"})

    async def aload(self) -> Inventory:
        return Inventory(hosts=Hosts())


class Dual(SyncOnly, AsyncOnly):
    def get_capabilities(self) -> frozenset[InventoryCapability]:
        return frozenset({"sync", "asyncio"})


class Declares:
    """Plugin whose declaration and methods are set per test."""

    def __init__(self, capabilities: Any, **methods: Any) -> None:
        self._capabilities = capabilities
        for name, method in methods.items():
            setattr(self, name, method)

    def get_capabilities(self) -> Any:
        return self._capabilities


def sync_load() -> Inventory:
    return Inventory(hosts=Hosts())


async def async_load() -> Inventory:
    await asyncio.sleep(0)
    return Inventory(hosts=Hosts())


@pytest.mark.parametrize(
    ("plugin", "expected"),
    [
        (SyncOnly(), frozenset({"sync"})),
        (AsyncOnly(), frozenset({"asyncio"})),
        (Dual(), frozenset({"sync", "asyncio"})),
    ],
)
def test_valid_declarations(plugin: Any, expected: frozenset[str]) -> None:
    assert _validate_capability_inventory_plugin("p", plugin) == expected


class NoReporter:
    def load(self) -> Inventory:
        return sync_load()


class NonCallableReporter:
    get_capabilities = frozenset({"sync"})

    def load(self) -> Inventory:
        return sync_load()


class BrokenReporterProperty:
    @property
    def get_capabilities(self) -> Any:
        msg = "reporter unavailable"
        raise RuntimeError(msg)


class AsyncReporter:
    async def get_capabilities(self) -> frozenset[InventoryCapability]:
        return frozenset({"sync"})

    def load(self) -> Inventory:
        return sync_load()


class FailingReporter:
    def get_capabilities(self) -> frozenset[InventoryCapability]:
        msg = "boom"
        raise RuntimeError(msg)


@pytest.mark.parametrize(
    ("plugin", "reason"),
    [
        (NonCallableReporter(), "get_capabilities must be a synchronous callable"),
        (AsyncReporter(), "get_capabilities must be a synchronous callable"),
        (Declares({"sync"}, load=sync_load), "nonempty frozenset"),
        (Declares(frozenset(), load=sync_load), "nonempty frozenset"),
        (Declares(frozenset({"threads"}), load=sync_load), "nonempty frozenset"),
        (Declares(frozenset({"sync"})), "sync capability requires"),
        (Declares(frozenset({"sync"}), load=async_load), "sync capability requires"),
        (Declares(frozenset({"asyncio"})), "asyncio capability requires"),
        (Declares(frozenset({"asyncio"}), aload=sync_load), "asyncio capability requires"),
        (Declares(frozenset({"sync", "asyncio"}), load=sync_load), "dual capability requires"),
        (Declares(frozenset({"sync", "asyncio"}), aload=async_load), "dual capability requires"),
    ],
)
def test_invalid_declarations(plugin: Any, reason: str) -> None:
    with pytest.raises(InventoryPluginContractError) as exc_info:
        _validate_capability_inventory_plugin("bad_plugin", plugin)

    assert exc_info.value.plugin_name == "bad_plugin"
    assert reason in exc_info.value.reason


@pytest.mark.parametrize(
    ("plugin", "cause"),
    [(NoReporter(), AttributeError), (BrokenReporterProperty(), RuntimeError)],
)
def test_inaccessible_reporter_chains_original_exception(
    plugin: Any, cause: type[Exception]
) -> None:
    with pytest.raises(InventoryPluginContractError) as exc_info:
        _validate_capability_inventory_plugin("bad_plugin", plugin)

    assert exc_info.value.reason == "get_capabilities could not be accessed"
    assert isinstance(exc_info.value.__cause__, cause)


def test_failing_reporter_chains_original_exception() -> None:
    with pytest.raises(InventoryPluginContractError) as exc_info:
        _validate_capability_inventory_plugin("bad_plugin", FailingReporter())

    assert exc_info.value.reason == "get_capabilities failed"
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_new_registers_have_their_own_dictionaries() -> None:
    dictionaries = [
        InventoryPluginRegister.available,
        CapabilityInventoryPluginRegister.available,
        AsyncTransformFunctionRegister.available,
    ]

    assert len({id(d) for d in dictionaries}) == len(dictionaries)
    assert TransformFunctionRegister.available is not CapabilityInventoryPluginRegister.available
    assert TransformFunctionRegister.available is not AsyncTransformFunctionRegister.available
