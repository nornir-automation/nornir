from __future__ import annotations

import pytest

from nornir.core.exceptions import (
    InventoryPluginAmbiguousError,
    InventoryPluginContractError,
    InventoryPluginNotSyncError,
    SyncAsyncMismatchError,
    TransformFunctionAmbiguousError,
    TransformFunctionNotSyncError,
)


def test_inventory_plugin_not_sync_error() -> None:
    error = InventoryPluginNotSyncError("api_inventory")

    assert isinstance(error, SyncAsyncMismatchError)
    assert error.plugin_name == "api_inventory"
    assert "'api_inventory'" in str(error)
    assert "await AInitNornir(...)" in str(error)


def test_transform_function_not_sync_error() -> None:
    error = TransformFunctionNotSyncError("vault_enrich")

    assert isinstance(error, SyncAsyncMismatchError)
    assert error.transform_name == "vault_enrich"
    assert "'vault_enrich'" in str(error)
    assert "async def" in str(error)
    assert "await AInitNornir(...)" in str(error)


@pytest.mark.parametrize(
    ("error", "name"),
    [
        (InventoryPluginAmbiguousError("api_inventory"), "'api_inventory'"),
        (TransformFunctionAmbiguousError("vault_enrich"), "'vault_enrich'"),
    ],
)
def test_ambiguous_errors_are_not_mode_mismatches(error: Exception, name: str) -> None:
    assert not isinstance(error, SyncAsyncMismatchError)
    assert name in str(error)
    assert "both" in str(error)
    assert "rename" in str(error)


def test_ambiguous_error_attributes() -> None:
    assert InventoryPluginAmbiguousError("api_inventory").plugin_name == "api_inventory"
    assert TransformFunctionAmbiguousError("vault_enrich").transform_name == "vault_enrich"


def test_inventory_plugin_contract_error() -> None:
    error = InventoryPluginContractError("api_inventory", "aload must be a coroutine function")

    assert not isinstance(error, SyncAsyncMismatchError)
    assert error.plugin_name == "api_inventory"
    assert error.reason == "aload must be a coroutine function"
    assert "'api_inventory'" in str(error)
    assert "aload must be a coroutine function" in str(error)
