from __future__ import annotations

import sys
import textwrap
from typing import TYPE_CHECKING

import pytest

from nornir import InitNornir
from nornir.core.exceptions import (
    OperationAlreadyRegisteredError,
    OperationContractNotFoundError,
    OperationEntryPointError,
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
    make_nornir,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from nornir.core.task import Task

pytestmark = pytest.mark.usefixtures("operation_registry")


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


def test_two_classes_with_one_name_raise() -> None:
    with pytest.raises(OperationAlreadyRegisteredError) as info:

        class OtherGetConfig(Operation[GetConfigInput, GetConfigOutput]):
            name = "get_config"

    assert str(info.value) == (
        "operation name 'get_config' is already defined by "
        "tests.core.operations_helpers.GetConfig; cannot define "
        "tests.core.test_operations_registry.test_two_classes_with_one_name_raise."
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
    exec(source, namespace)  # noqa: S102

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


def test_malformed_implementation_name_raises_and_loading_is_retried(site: Path) -> None:
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
    assert OperationRegistry._loaded is False
    with pytest.raises(OperationEntryPointError):
        OperationRegistry.load()


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
        nr.run_operation(GetConfig, connection="napalm")
