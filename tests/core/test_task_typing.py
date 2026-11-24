"""Type errors the caller of a plain task must see, checked by running mypy on snippets."""

from __future__ import annotations

import pickle  # noqa: S403 - round-trips results built by the test
from typing import TYPE_CHECKING

import nornir.core
import nornir.core.task
from nornir.core.task import AggregatedResult, MultiResult, Result
from tests.core.test_operations_typing import check

if TYPE_CHECKING:
    from pathlib import Path

PRELUDE = """
    from dataclasses import dataclass

    from nornir.core import Nornir
    from nornir.core.task import Result, Task

    @dataclass
    class Facts:
        hostname: str
        version: str

    def get_facts(task: Task) -> Result[Facts]:
        return Result(task.host, result=Facts(hostname=task.host.name, version="17.9"))

    def get_version(task: Task) -> tuple[int, int]:
        return (17, 9)
"""


def test_reading_a_missing_field_of_a_run_result_is_rejected(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def report(nr: Nornir) -> None:
        for multi in nr.run(task=get_facts).values():
            if not multi.failed:
                print(multi.result.verison)
    """,
    )

    assert '"Facts" has no attribute "verison"' in report


def test_using_a_subtask_result_as_another_type_is_rejected(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def needs_upgrade(task: Task, target: str) -> bool:
        current = task.run(task=get_version).result
        return current < target
    """,
    )

    assert 'Unsupported operand types for < ("tuple[int, int]" and "str")' in report


def test_a_task_returning_a_wrong_result_type_is_rejected(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def count(nr: Nornir) -> int:
        return nr.run(get_facts)["r1"].result
    """,
    )

    assert 'Incompatible return value type (got "Facts", expected "int")' in report


def test_an_untyped_task_reports_nothing(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    from typing import Any

    def untyped(task: Task) -> Any:
        return 1

    def report(nr: Nornir) -> None:
        print(nr.run(untyped)["r1"].result.anything)
    """,
    )

    assert "Success: no issues found" in report


def test_assigning_the_result_of_a_multi_result_is_rejected(tmp_path: Path) -> None:
    # The assignment would not change multi[0].result, which print_result and processors read.
    report = check(
        tmp_path,
        PRELUDE
        + """
    from nornir.core.task import MultiResult

    def fix(multi: MultiResult) -> None:
        multi.result = 5
    """,
    )

    assert 'Property "result" defined in "MultiResult" is read-only' in report


def test_the_result_type_variable_is_not_public() -> None:
    assert not hasattr(nornir.core, "ResultT")
    assert not hasattr(nornir.core.task, "ResultT")


def test_the_type_parameters_do_not_change_the_runtime() -> None:
    multi = MultiResult[int]("task")
    multi.append(Result(None, result=1))
    assert type(multi) is MultiResult
    assert multi.result == 1
    assert "result" not in vars(MultiResult)
    multi[0].result = 2
    assert multi.result == 2
    result = AggregatedResult[int]("task", r1=multi)
    assert type(result) is AggregatedResult
    assert pickle.loads(pickle.dumps(result))["r1"].result == 2  # noqa: S301 - data from this test
