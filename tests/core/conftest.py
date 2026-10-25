from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

import pytest

from nornir.core.operations import OperationRegistry
from nornir.core.plugins.inventory import (
    AsyncTransformFunctionRegister,
    CapabilityInventoryPluginRegister,
    InventoryPluginRegister,
    TransformFunctionRegister,
)
from tests.core.inventory_plugins import RECORDER

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def isolated_inventory_registries() -> Iterator[None]:
    """Restore the inventory and transform registers and reset the call recorder.

    The legacy registers share one dictionary with the runner and connection registers,
    so it is restored in place and never replaced: replacing it would detach them.
    """
    dictionaries: tuple[dict[str, Any], ...] = (
        InventoryPluginRegister.available,
        TransformFunctionRegister.available,
        CapabilityInventoryPluginRegister.available,
        AsyncTransformFunctionRegister.available,
    )
    snapshots = [(available, dict(available)) for available in dictionaries]
    RECORDER.reset()
    yield
    for available, snapshot in snapshots:
        available.clear()
        available.update(snapshot)
    RECORDER.reset()


@pytest.fixture
def operation_registry() -> Iterator[type[OperationRegistry]]:
    """Restore the Operation registry after the test, and skip installed entry points.

    Operation classes defined by test modules stay registered; registrations made by the
    test are removed.

    Yields:
        The registry.

    """
    with OperationRegistry._lock:
        contracts = dict(OperationRegistry._contracts)
        registrations = dict(OperationRegistry._registrations)
        loaded = OperationRegistry._loaded
        OperationRegistry._registrations.clear()
        OperationRegistry._loaded = True
    yield OperationRegistry
    with OperationRegistry._lock:
        OperationRegistry._contracts.clear()
        OperationRegistry._contracts.update(contracts)
        OperationRegistry._registrations.clear()
        OperationRegistry._registrations.update(registrations)
        OperationRegistry._loaded = loaded


@pytest.fixture
def release() -> Iterator[threading.Event]:
    """Provide the event that blocked test tasks wait on.

    It is set at teardown, so no blocked worker thread outlives the test.

    Yields:
        The event.

    """
    event = threading.Event()
    yield event
    event.set()
