from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

import pytest

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
def release() -> Iterator[threading.Event]:
    """Provide the event that blocked test tasks wait on.

    It is set at teardown, so no blocked worker thread outlives the test.

    Yields:
        The event.

    """
    event = threading.Event()
    yield event
    event.set()
