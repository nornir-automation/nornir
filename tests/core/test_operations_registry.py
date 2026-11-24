from __future__ import annotations

import importlib
import sys
import textwrap
import threading
import time
from typing import TYPE_CHECKING, TypedDict, TypeVar

import pytest

from nornir import InitNornir
from nornir.core.exceptions import (
    OperationAlreadyRegisteredError,
    OperationContractNotFoundError,
    OperationEntryPointError,
    OperationNotRegisteredError,
)
from nornir.core.operations import Operation, OperationRegistry, RegistrationSource
from nornir.plugins.runners import SerialRunner
from tests.core.operations_helpers import (
    GetConfig,
    GetConfigInput,
    GetConfigOutput,
    aios_get_config,
    eos_get_config,
    ios_get_config,
    junos_get_config,
    make_nornir,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from nornir.core.task import Task

pytestmark = pytest.mark.usefixtures("operation_registry")

InT = TypeVar("InT")
OutT = TypeVar("OutT")


def other_ios_get_config(task: Task, params: GetConfigInput) -> GetConfigOutput:
    return GetConfigOutput(config="other")


# --- Registration by call ---------------------------------------------------------------


def test_registering_the_same_task_twice_is_accepted() -> None:
    first = OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=ios_get_config
    )
    second = OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=ios_get_config
    )

    assert first is second
    assert first.source == RegistrationSource(
        kind="call", module="tests.core.operations_helpers", qualname="ios_get_config"
    )


def test_a_different_task_for_a_taken_key_raises_with_both_sources() -> None:
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=ios_get_config
    )

    with pytest.raises(OperationAlreadyRegisteredError) as info:
        OperationRegistry.register(
            operation="get_config", platform="ios", connection="napalm", task=other_ios_get_config
        )

    assert str(info.value) == (
        "cannot register tests.core.test_operations_registry.other_ios_get_config for "
        "get_config.ios.napalm: tests.core.operations_helpers.ios_get_config already "
        "registered it. Pass replace=True to override."
    )


def test_replace_true_replaces_and_the_run_uses_the_new_task() -> None:
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=ios_get_config
    )
    OperationRegistry.register(
        operation="get_config",
        platform="ios",
        connection="napalm",
        task=other_ios_get_config,
        replace=True,
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    results = list(nr.run_operation(GetConfig, connection="napalm").results())

    assert results[0].result == GetConfigOutput(config="other")


@pytest.mark.parametrize(
    ("operation", "platform", "connection"),
    [("get_config", None, "napalm"), ("get_config", "", "napalm"), ("get_config", "ios", "")],
)
def test_empty_or_none_key_parts_are_rejected(
    operation: str, platform: str | None, connection: str
) -> None:
    with pytest.raises(ValueError, match="must be a non-empty string"):
        OperationRegistry.register(
            operation=operation,
            platform=platform,  # type: ignore[arg-type]
            connection=connection,
            task=ios_get_config,
        )


def test_deregister_removes_the_task() -> None:
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=ios_get_config
    )
    OperationRegistry.deregister(operation="get_config", platform="ios", connection="napalm")

    assert OperationRegistry.operations()[0].implementations == ()


def test_two_classes_with_one_name_raise_when_the_name_is_looked_up() -> None:
    class OtherGetConfig(Operation[GetConfigInput, GetConfigOutput]):
        name = "get_config"

    nr = make_nornir(SerialRunner(), {"r1": "ios"})
    for lookup in (
        lambda: OperationRegistry.contract("get_config"),
        lambda: nr.run_operation(GetConfig, connection="napalm"),
        lambda: nr.run_operation(OtherGetConfig, connection="napalm"),
    ):
        with pytest.raises(OperationAlreadyRegisteredError) as info:
            lookup()
        assert str(info.value) == (
            "operation name 'get_config' is already defined by "
            "tests.core.operations_helpers.GetConfig; cannot define "
            "tests.core.test_operations_registry."
            "test_two_classes_with_one_name_raise_when_the_name_is_looked_up."
            "<locals>.OtherGetConfig."
        )


def test_the_same_definition_executed_again_replaces_the_class() -> None:
    source = textwrap.dedent(
        """
        from nornir.core.operations import Operation

        class In:
            pass

        class Again(Operation[In, In]):
            name = "again"
        """
    )
    namespace: dict[str, object] = {"__name__": "notebook_cell"}
    exec(source, namespace)  # noqa: S102 - a notebook cell executed twice
    first = OperationRegistry.contract("again")
    namespace = {"__name__": "notebook_cell"}
    exec(source, namespace)  # noqa: S102 - the same notebook cell executed again

    assert OperationRegistry.contract("again") is not first
    assert OperationRegistry.contract("again") is namespace["Again"]


def test_type_arguments_must_be_classes() -> None:
    with pytest.raises(TypeError, match="must be classes"):

        class Broken(Operation["GetConfigInput", GetConfigOutput]):
            name = "broken"


def test_a_base_without_name_is_not_registered() -> None:
    class Base(Operation[GetConfigInput, GetConfigOutput]):
        pass

    class Concrete(Base):
        name = "concrete"

    names = [info.name for info in OperationRegistry.operations()]
    assert "concrete" in names
    assert Concrete.input_model is GetConfigInput
    assert Concrete.output_model is GetConfigOutput


def test_task_for_a_name_with_no_contract() -> None:
    OperationRegistry.register(
        operation="not_defined", platform="ios", connection="napalm", task=ios_get_config
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    infos = {info.name: info for info in OperationRegistry.operations()}
    assert infos["not_defined"].operation is None
    assert infos["not_defined"].input_model is None
    with pytest.raises(OperationContractNotFoundError, match="'not_defined'"):
        nr.run_operation("not_defined", connection="napalm")


def test_listing_reports_models_kind_and_source_without_calling_tasks() -> None:
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=aios_get_config
    )
    OperationRegistry.register(
        operation="get_config", platform="eos", connection="napalm", task=eos_get_config
    )

    info = next(i for i in OperationRegistry.operations() if i.name == "get_config")

    assert info.operation is GetConfig
    assert info.input_model is GetConfigInput
    assert info.output_model is GetConfigOutput
    assert [(r.platform, r.kind, r.source.qualname) for r in info.implementations] == [
        ("eos", "sync", "eos_get_config"),
        ("ios", "async", "aios_get_config"),
    ]


# --- Entry points -----------------------------------------------------------------------


def make_distribution(
    root: Path,
    name: str,
    module: str,
    code: str,
    entry_points: dict[str, dict[str, str]],
) -> None:
    """Write an installed distribution under ``root``: one module and its metadata."""
    (root / f"{module}.py").write_text(textwrap.dedent(code), encoding="utf-8")
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


CONTRACT_CODE = """
    from dataclasses import dataclass
    from nornir.core.operations import Operation

    @dataclass
    class FactsInput:
        pass

    @dataclass
    class FactsOutput:
        vendor: str

    class GetFacts(Operation[FactsInput, FactsOutput]):
        name = "get_facts"
"""

TASKS_CODE = """
    from {contract} import FactsOutput

    def ios_facts(task, params):
        return FactsOutput(vendor="cisco")

    async def eos_facts(task, params):
        return FactsOutput(vendor="arista")
"""


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


def start_loading() -> None:
    OperationRegistry._loaded = False


def test_entry_points_declare_contracts_and_implementations(site: Path) -> None:
    make_distribution(
        site,
        "ops_contracts_a",
        "ops_contracts_a",
        CONTRACT_CODE,
        {"nornir.plugins.operations": {"get_facts": "ops_contracts_a:GetFacts"}},
    )
    make_distribution(
        site,
        "ops_tasks_a",
        "ops_tasks_a",
        TASKS_CODE.format(contract="ops_contracts_a"),
        {
            "nornir.plugins.operation_tasks": {
                "get_facts.ios.napalm": "ops_tasks_a:ios_facts",
                "get_facts.eos.napalm": "ops_tasks_a:eos_facts",
            }
        },
    )
    start_loading()

    info = next(i for i in OperationRegistry.operations() if i.name == "get_facts")

    assert info.input_model is not None
    assert info.input_model.__name__ == "FactsInput"
    assert [
        (r.platform, r.kind, r.source.distribution, r.source.entry_point)
        for r in info.implementations
    ] == [
        ("eos", "async", "ops_tasks_a", "get_facts.eos.napalm"),
        ("ios", "sync", "ops_tasks_a", "get_facts.ios.napalm"),
    ]
    assert str(info.implementations[1].source) == (
        "distribution 'ops_tasks_a' (entry point 'get_facts.ios.napalm')"
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})
    results = list(nr.run_operation("get_facts", connection="napalm").results())
    assert results[0].result.vendor == "cisco"


def test_contract_with_no_implementation_is_listed(site: Path) -> None:
    make_distribution(
        site,
        "ops_contracts_b",
        "ops_contracts_b",
        CONTRACT_CODE,
        {"nornir.plugins.operations": {"get_facts": "ops_contracts_b:GetFacts"}},
    )
    start_loading()

    info = next(i for i in OperationRegistry.operations() if i.name == "get_facts")

    assert info.output_model is not None
    assert info.output_model.__name__ == "FactsOutput"
    assert info.implementations == ()


def test_contract_entry_point_must_match_the_class_name(site: Path) -> None:
    make_distribution(
        site,
        "ops_contracts_c",
        "ops_contracts_c",
        CONTRACT_CODE,
        {"nornir.plugins.operations": {"facts": "ops_contracts_c:GetFacts"}},
    )
    start_loading()

    with pytest.raises(OperationEntryPointError, match="'ops_contracts_c'"):
        OperationRegistry.operations()


def test_malformed_implementation_name_raises_each_time(site: Path) -> None:
    make_distribution(
        site,
        "ops_tasks_d",
        "ops_tasks_d",
        "def ios_facts(task, params):\n    return None\n",
        {"nornir.plugins.operation_tasks": {"get_facts.ios": "ops_tasks_d:ios_facts"}},
    )
    start_loading()

    with pytest.raises(OperationEntryPointError) as info:
        OperationRegistry.load()

    assert str(info.value) == (
        "distribution 'ops_tasks_d' declares entry point 'get_facts.ios': in "
        "'nornir.plugins.operation_tasks', the name must be "
        "'<operation>.<platform>.<connection>'."
    )
    with pytest.raises(OperationEntryPointError):
        OperationRegistry.load()
    with pytest.raises(OperationEntryPointError):
        OperationRegistry.contract("get_facts")


def test_two_distributions_declaring_one_key_raise_with_both(site: Path) -> None:
    for dist in ("ops_tasks_e", "ops_tasks_f"):
        make_distribution(
            site,
            dist,
            dist,
            "def ios_facts(task, params):\n    return None\n",
            {"nornir.plugins.operation_tasks": {"get_facts.ios.napalm": f"{dist}:ios_facts"}},
        )
    start_loading()

    with pytest.raises(OperationAlreadyRegisteredError) as info:
        OperationRegistry.load()

    message = str(info.value)
    assert "distribution 'ops_tasks_e'" in message
    assert "distribution 'ops_tasks_f'" in message


def test_init_nornir_does_not_load_entry_points(site: Path) -> None:
    make_distribution(
        site,
        "ops_tasks_g",
        "ops_tasks_g",
        "def ios_facts(task, params):\n    return None\n",
        {"nornir.plugins.operation_tasks": {"broken": "ops_tasks_g:ios_facts"}},
    )
    hosts = site / "hosts.yaml"
    hosts.write_text("r1:\n  platform: ios\n", encoding="utf-8")
    start_loading()

    nr = InitNornir(
        inventory={"plugin": "SimpleInventory", "options": {"host_file": str(hosts)}},
        runner={"plugin": "serial"},
        logging={"enabled": False},
    )

    assert list(nr.inventory.hosts) == ["r1"]
    assert "ops_tasks_g" not in sys.modules
    with pytest.raises(OperationEntryPointError):
        OperationRegistry.load()


def test_replace_before_the_first_run_overrides_an_installed_task(site: Path) -> None:
    make_distribution(
        site,
        "ops_tasks_h",
        "ops_tasks_h",
        "def ios_get_config(task, params):\n    return None\n",
        {"nornir.plugins.operation_tasks": {"get_config.ios.napalm": "ops_tasks_h:ios_get_config"}},
    )
    start_loading()

    OperationRegistry.register(
        operation="get_config",
        platform="ios",
        connection="napalm",
        task=ios_get_config,
        replace=True,
    )

    assert OperationRegistry.get("get_config", "ios", "napalm").task is ios_get_config


def test_deregister_before_the_first_run_removes_an_installed_task(site: Path) -> None:
    make_distribution(
        site,
        "ops_tasks_i",
        "ops_tasks_i",
        "def ios_get_config(task, params):\n    return None\n",
        {"nornir.plugins.operation_tasks": {"get_config.ios.napalm": "ops_tasks_i:ios_get_config"}},
    )
    start_loading()

    OperationRegistry.deregister(operation="get_config", platform="ios", connection="napalm")

    with pytest.raises(OperationNotRegisteredError):
        OperationRegistry.get("get_config", "ios", "napalm")


def broken_distribution(root: Path) -> None:
    """Install a distribution whose module imports a dependency that is not installed."""
    make_distribution(
        root,
        "ops_tasks_broken",
        "ops_tasks_broken",
        "import ops_dependency_not_installed\n",
        {"nornir.plugins.operation_tasks": {"get_facts.ios.napalm": "ops_tasks_broken:facts"}},
    )
    start_loading()


def test_a_broken_package_does_not_stop_operations_of_other_packages(site: Path) -> None:
    broken_distribution(site)
    OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=ios_get_config
    )
    nr = make_nornir(SerialRunner(), {"r1": "ios"})

    result = nr.run_operation(GetConfig, connection="napalm").result()

    assert not result.failed


def test_a_broken_package_is_named_in_the_error(site: Path) -> None:
    broken_distribution(site)

    for lookup in (OperationRegistry.load, lambda: OperationRegistry.contract("get_facts")):
        with pytest.raises(OperationEntryPointError) as info:
            lookup()
        assert str(info.value) == (
            "distribution 'ops_tasks_broken' declares entry point 'get_facts.ios.napalm': "
            "cannot load 'ops_tasks_broken:facts': ModuleNotFoundError: No module named "
            "'ops_dependency_not_installed'"
        )
        assert isinstance(info.value.__cause__, ModuleNotFoundError)


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
        name = "shared_name"

    def plain_task(task):
        return "a task that does not use Operations"
"""


def test_two_packages_defining_one_operation_name_can_both_be_imported(site: Path) -> None:
    for module in ("ops_vendor_a", "ops_vendor_b"):
        (site / f"{module}.py").write_text(textwrap.dedent(SHARED_NAME_CODE), encoding="utf-8")

    importlib.import_module("ops_vendor_a")
    importlib.import_module("ops_vendor_b")

    with pytest.raises(OperationAlreadyRegisteredError, match=r"ops_vendor_b\.GetConfig"):
        OperationRegistry.contract("shared_name")


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
        name = "get_slow"
"""


def test_loading_while_another_thread_imports_an_operation_does_not_deadlock(
    site: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A deadlock leaves both threads blocked for good. They hold locks created for this
    # test, so the other tests can still use the registry.
    monkeypatch.setattr(OperationRegistry, "_lock", threading.RLock())
    monkeypatch.setattr(OperationRegistry, "_load_lock", threading.RLock())
    make_distribution(
        site,
        "ops_slow",
        "ops_slow",
        SLOW_CONTRACT_CODE,
        {"nornir.plugins.operations": {"get_slow": "ops_slow:GetSlow"}},
    )
    start_loading()

    importer = threading.Thread(target=importlib.import_module, args=("ops_slow",), daemon=True)
    loader = threading.Thread(target=OperationRegistry.load, daemon=True)
    importer.start()
    time.sleep(0.1)  # The importer now holds the import lock of ops_slow.
    loader.start()
    importer.join(5)
    loader.join(5)

    assert not importer.is_alive()
    assert not loader.is_alive()


# A module named by an entry point that also registers a task by call while it is imported.
# The register() call comes before the function the entry point names.
REGISTERING_TASKS_CODE = """
    import time
    from nornir.core.operations import OperationRegistry

    def eos_get_config(task, params):
        return None

    time.sleep({delay})
    OperationRegistry.register(
        operation="get_config", platform="eos", connection="napalm", task=eos_get_config
    )

    def ios_get_config(task, params):
        return None
"""


def test_a_package_that_registers_a_task_while_it_is_imported_loads(site: Path) -> None:
    make_distribution(
        site,
        "ops_registering",
        "ops_registering",
        REGISTERING_TASKS_CODE.format(delay=0),
        {
            "nornir.plugins.operation_tasks": {
                "get_config.ios.napalm": "ops_registering:ios_get_config"
            }
        },
    )
    start_loading()

    registration = OperationRegistry.get("get_config", "ios", "napalm")

    assert registration.task.__name__ == "ios_get_config"


def test_registering_while_another_thread_loads_the_entry_points_does_not_deadlock(
    site: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A deadlock leaves both threads blocked for good. They hold locks created for this
    # test, so the other tests can still use the registry.
    monkeypatch.setattr(OperationRegistry, "_lock", threading.RLock())
    monkeypatch.setattr(OperationRegistry, "_load_lock", threading.RLock())
    make_distribution(
        site,
        "ops_registering_slow",
        "ops_registering_slow",
        REGISTERING_TASKS_CODE.format(delay=0.5),
        {
            "nornir.plugins.operation_tasks": {
                "get_config.ios.napalm": "ops_registering_slow:ios_get_config"
            }
        },
    )
    start_loading()

    importer = threading.Thread(
        target=importlib.import_module, args=("ops_registering_slow",), daemon=True
    )
    loader = threading.Thread(target=OperationRegistry.load, daemon=True)
    importer.start()
    time.sleep(0.1)  # The importer now holds the import lock of ops_registering_slow.
    loader.start()
    importer.join(5)
    loader.join(5)

    assert not importer.is_alive()
    assert not loader.is_alive()


def working_and_broken_get_config(root: Path) -> None:
    """Install two distributions that implement get_config with napalm.

    ``ops_get_config_ios`` implements it for ios and loads. ``ops_get_config_junos``
    implements it for junos, and its module imports a dependency that is not installed.
    """
    make_distribution(
        root,
        "ops_get_config_ios",
        "ops_get_config_ios",
        "from tests.core.operations_helpers import ios_get_config\n",
        {
            "nornir.plugins.operation_tasks": {
                "get_config.ios.napalm": "ops_get_config_ios:ios_get_config"
            }
        },
    )
    make_distribution(
        root,
        "ops_get_config_junos",
        "ops_get_config_junos",
        "import ops_dependency_not_installed\n",
        {
            "nornir.plugins.operation_tasks": {
                "get_config.junos.napalm": "ops_get_config_junos:junos_get_config"
            }
        },
    )
    start_loading()


def test_a_broken_package_fails_only_the_hosts_of_its_platform(site: Path) -> None:
    working_and_broken_get_config(site)
    nr = make_nornir(SerialRunner(), {"r1": "ios", "r3": "junos"})

    result = nr.run_operation(GetConfig, connection="napalm").result()

    assert not result["r1"].failed
    assert isinstance(result["r3"].exception, OperationEntryPointError)


def test_replace_overrides_a_task_whose_package_failed_to_load(site: Path) -> None:
    working_and_broken_get_config(site)

    OperationRegistry.register(
        operation="get_config",
        platform="junos",
        connection="napalm",
        task=junos_get_config,
        replace=True,
    )

    assert OperationRegistry.get("get_config", "junos", "napalm").task is junos_get_config


# --- Definitions of Operation classes ---------------------------------------------------


def test_a_model_that_isinstance_rejects_is_rejected_when_the_operation_is_defined() -> None:
    class FactsDict(TypedDict):
        vendor: str

    with pytest.raises(TypeError, match=r"FactsDict cannot be a model .* isinstance\(\)"):

        class GetFactsDict(Operation[GetConfigInput, FactsDict]):
            name = "get_facts_dict"


def test_a_generic_base_without_name_can_be_subclassed() -> None:
    class NapalmOperation(Operation[InT, OutT]):
        """A base for the Operations that use NAPALM."""

    class GetNapalmConfig(NapalmOperation[GetConfigInput, GetConfigOutput]):
        name = "get_napalm_config"

    assert GetNapalmConfig.input_model is GetConfigInput
    assert GetNapalmConfig.output_model is GetConfigOutput
    assert OperationRegistry.contract("get_napalm_config") is GetNapalmConfig


def test_a_base_with_one_model_receives_the_other_from_its_subclass() -> None:
    class ConfigOperation(Operation[GetConfigInput, OutT]):
        """A base for the Operations that read the configuration."""

    class GetConfigText(ConfigOperation[GetConfigOutput]):
        name = "get_config_text"

    assert GetConfigText.input_model is GetConfigInput
    assert GetConfigText.output_model is GetConfigOutput


def test_a_named_operation_with_type_variables_raises() -> None:
    with pytest.raises(TypeError, match="give the input and output models"):

        class Unfinished(Operation[GetConfigInput, OutT]):
            name = "unfinished"


def test_registering_the_same_bound_method_twice_is_accepted() -> None:
    class Driver:
        def get_config(self, task: Task, params: GetConfigInput) -> GetConfigOutput:
            return GetConfigOutput(config="driver")

    driver = Driver()

    first = OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=driver.get_config
    )
    second = OperationRegistry.register(
        operation="get_config", platform="ios", connection="napalm", task=driver.get_config
    )

    assert second is first
