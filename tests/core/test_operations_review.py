"""Review of #1115: each test describes one problem found in review and fails on purpose.

The tests are meant to be merged together with the fixes, or removed when a finding is
not addressed. See the pull request description for the reasoning behind each test.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
import textwrap
import threading
import time
from typing import TYPE_CHECKING, Any, TypedDict, TypeVar

import pytest

from nornir.core.exceptions import (
    OperationEntryPointError,
    OperationNotRegisteredError,
    RunnerCapabilityError,
    RunnerNotAsyncError,
    RunnerNotSyncError,
)
from nornir.core.inventory import ConnectionOptions
from nornir.core.operations import Operation, OperationRegistry
from nornir.plugins.runners import AsyncioRunner, SerialRunner, ThreadedRunner
from tests.core.operations_helpers import (
    GetConfig,
    GetConfigInput,
    GetConfigOutput,
    aios_get_config,
    ios_get_config,
    make_nornir,
    register_get_config,
)
from tests.core.run_helpers import EventLog

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from nornir.core.inventory import Host
    from nornir.core.task import Task

pytestmark = pytest.mark.usefixtures("operation_registry")

InT = TypeVar("InT")
OutT = TypeVar("OutT")


@pytest.fixture
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Put a directory on ``sys.path``; its modules are unloaded after the test.

    Yields:
        The directory.

    """
    monkeypatch.syspath_prepend(str(tmp_path))
    before = set(sys.modules)
    yield tmp_path
    for module in set(sys.modules) - before:
        del sys.modules[module]


def make_distribution(
    root: Path, name: str, code: str, entry_points: dict[str, dict[str, str]]
) -> None:
    """Write an installed distribution under ``root``: one module named ``name``."""
    (root / f"{name}.py").write_text(textwrap.dedent(code), encoding="utf-8")
    dist_info = root / f"{name}-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n", encoding="utf-8"
    )
    lines = []
    for group, entries in entry_points.items():
        lines.append(f"[{group}]")
        lines.extend(f"{key} = {value}" for key, value in entries.items())
    (dist_info / "entry_points.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def installed_get_config(root: Path) -> None:
    """Install a distribution that implements get_config for ios with napalm."""
    make_distribution(
        root,
        "review_installed_ops",
        "def ios_get_config(task, params):\n    return None\n",
        {
            "nornir.plugins.operation_tasks": {
                "get_config.ios.napalm": "review_installed_ops:ios_get_config"
            }
        },
    )
    OperationRegistry._loaded = False


# --- Registry changes made before the entry points are loaded ---------------------------


def test_replace_before_the_first_run_overrides_an_installed_task(site: Path) -> None:
    installed_get_config(site)

    OperationRegistry.register(
        operation="get_config",
        platform="ios",
        connection="napalm",
        task=ios_get_config,
        replace=True,
    )

    assert OperationRegistry.get("get_config", "ios", "napalm").task is ios_get_config


def test_deregister_before_the_first_run_removes_an_installed_task(site: Path) -> None:
    installed_get_config(site)

    OperationRegistry.deregister(operation="get_config", platform="ios", connection="napalm")

    with pytest.raises(OperationNotRegisteredError):
        OperationRegistry.get("get_config", "ios", "napalm")


# --- Output models that isinstance() cannot check ---------------------------------------


def test_an_output_model_that_isinstance_rejects_does_not_stop_the_run() -> None:
    class FactsDict(TypedDict):
        vendor: str

    try:

        class GetFactsDict(Operation[GetConfigInput, FactsDict]):
            name = "review_get_facts_dict"

    except TypeError:
        return  # Rejecting the model when the Operation is defined also resolves it.

    def ios_facts(task: Task, params: GetConfigInput) -> FactsDict:
        return FactsDict(vendor="cisco")

    OperationRegistry.register(
        operation="review_get_facts_dict", platform="ios", connection="napalm", task=ios_facts
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios", "r2": "ios"})

    result = nr.run_operation(GetFactsDict, connection="napalm").result()

    assert set(result) == {"r1", "r2"}


# --- Operation names shared by two packages ---------------------------------------------

SHARED_NAME_CODE = """
    from dataclasses import dataclass
    from nornir.core.operations import Operation

    @dataclass
    class ConfigInput:
        pass

    @dataclass
    class ConfigOutput:
        config: str

    class GetConfig(Operation[ConfigInput, ConfigOutput]):
        name = "review_shared_name"

    def plain_task(task):
        return "a task that does not use Operations"
"""


def test_two_packages_defining_one_operation_name_can_both_be_imported(site: Path) -> None:
    for module in ("review_vendor_a", "review_vendor_b"):
        (site / f"{module}.py").write_text(textwrap.dedent(SHARED_NAME_CODE), encoding="utf-8")

    importlib.import_module("review_vendor_a")
    importlib.import_module("review_vendor_b")


# --- Platform of the connection ---------------------------------------------------------


def test_the_platform_of_the_connection_selects_the_task() -> None:
    OperationRegistry.register(
        operation="get_config", platform="cisco_ios", connection="netmiko", task=ios_get_config
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})
    nr.inventory.hosts["r1"].connection_options["netmiko"] = ConnectionOptions(platform="cisco_ios")

    result = nr.run_operation(GetConfig, connection="netmiko").result()

    assert not result.failed


# --- Entry points that cannot be loaded -------------------------------------------------


def broken_distribution(root: Path) -> None:
    """Install a distribution whose module imports a dependency that is not installed."""
    make_distribution(
        root,
        "review_broken_ops",
        "import review_dependency_not_installed\n",
        {"nornir.plugins.operation_tasks": {"get_facts.ios.napalm": "review_broken_ops:facts"}},
    )
    OperationRegistry._loaded = False


def test_a_broken_package_does_not_stop_operations_of_other_packages(site: Path) -> None:
    broken_distribution(site)
    register_get_config()
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    result = nr.run_operation(GetConfig, connection="napalm").result()

    assert not result.failed


def test_a_broken_package_is_named_in_the_error(site: Path) -> None:
    broken_distribution(site)

    with pytest.raises(OperationEntryPointError, match="review_broken_ops"):
        OperationRegistry.load()


# --- Generic base classes ---------------------------------------------------------------


def test_a_generic_base_without_name_can_be_subclassed() -> None:
    class NapalmOperation(Operation[InT, OutT]):
        """A base for the Operations that use NAPALM."""

    class GetNapalmConfig(NapalmOperation[GetConfigInput, GetConfigOutput]):
        name = "review_get_napalm_config"

    assert GetNapalmConfig.input_model is GetConfigInput
    assert GetNapalmConfig.output_model is GetConfigOutput


# --- Registering a bound method again ---------------------------------------------------


def test_registering_the_same_bound_method_twice_is_accepted() -> None:
    class Driver:
        def get_config(self, task: Task, params: GetConfigInput) -> GetConfigOutput:
            return GetConfigOutput(config="driver")

    driver = Driver()

    for _ in range(2):
        OperationRegistry.register(
            operation="get_config", platform="ios", connection="napalm", task=driver.get_config
        )


# --- Loading the entry points while another thread imports an Operation -----------------

SLOW_CONTRACT_CODE = """
    import time
    from dataclasses import dataclass
    from nornir.core.operations import Operation

    time.sleep(0.5)

    @dataclass
    class SlowInput:
        pass

    @dataclass
    class SlowOutput:
        pass

    class GetSlow(Operation[SlowInput, SlowOutput]):
        name = "review_get_slow"
"""


def test_loading_while_another_thread_imports_an_operation_does_not_deadlock(
    site: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A deadlock leaves both threads blocked for good. They hold a lock created for this
    # test, so the other tests can still use the registry.
    monkeypatch.setattr(OperationRegistry, "_lock", threading.RLock())
    make_distribution(
        site,
        "review_slow_ops",
        SLOW_CONTRACT_CODE,
        {"nornir.plugins.operations": {"review_get_slow": "review_slow_ops:GetSlow"}},
    )
    OperationRegistry._loaded = False

    importer = threading.Thread(
        target=importlib.import_module, args=("review_slow_ops",), daemon=True
    )
    loader = threading.Thread(target=OperationRegistry.load, daemon=True)
    importer.start()
    time.sleep(0.1)  # The importer now holds the import lock of review_slow_ops.
    loader.start()
    importer.join(5)
    loader.join(5)

    assert not importer.is_alive()
    assert not loader.is_alive()


# --- Per-host input built by a coroutine function ---------------------------------------


def test_arun_operation_awaits_an_async_params_function() -> None:
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=aios_get_config
    )

    async def startup_config(host: Host) -> GetConfigInput:
        await asyncio.sleep(0)
        return GetConfigInput(retrieve="startup")

    # The signature of arun_operation accepts only a synchronous callable.
    params: Any = startup_config

    async def scenario() -> None:
        nr = make_nornir(AsyncioRunner(), {"r1": "ios"})
        result = await nr.arun_operation(GetConfig, params, connection="napalm").result()
        assert not result.failed
        assert result["r1"][0].result == GetConfigOutput(config="ios startup r1")

    asyncio.run(scenario())


# --- What processors see ----------------------------------------------------------------


def test_task_instance_started_receives_the_selected_task_and_its_input() -> None:
    seen: list[tuple[str, dict[str, Any]]] = []

    class Recorder(EventLog):
        def task_instance_started(self, task: Task, host: Host) -> None:
            seen.append((task.task.__name__, dict(task.params)))

    register_get_config()
    nr = make_nornir(SerialRunner(), {"r1": "ios"}, processors=[Recorder()])

    nr.run_operation(GetConfig, connection="napalm").result()

    assert seen == [("ios_get_config", {"params": GetConfigInput()})]


# --- Error messages name the Operation entry points -------------------------------------


def test_submit_operation_on_serial_runner_suggests_run_operation() -> None:
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    with pytest.raises(RunnerCapabilityError) as info:
        nr.submit_operation(GetConfig, connection="napalm")

    assert "'stream'" not in str(info.value)
    assert "run_operation" in str(info.value)


def test_run_operation_on_asyncio_runner_suggests_arun_operation() -> None:
    nr = make_nornir(AsyncioRunner(), {"r1": "ios"})

    with pytest.raises(RunnerNotSyncError, match="arun_operation"):
        nr.run_operation(GetConfig, connection="napalm")


def test_arun_operation_on_threaded_runner_suggests_run_operation() -> None:
    nr = make_nornir(ThreadedRunner(num_workers=1), {"r1": "ios"})

    with pytest.raises(RunnerNotAsyncError, match="run_operation"):
        nr.arun_operation(GetConfig, connection="napalm")


def test_async_task_selected_on_a_sync_run_suggests_arun_operation() -> None:
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=aios_get_config
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    result = nr.run_operation(GetConfig, connection="napalm").result()

    assert "arun_operation" in str(result["r1"].exception)
