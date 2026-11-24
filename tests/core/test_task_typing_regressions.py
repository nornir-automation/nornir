"""Type-check regressions for Nornir 3.6.1 code, found in the review of PR #1129.

Each snippet below is code a Nornir 3.6.1 user can write today. Unless a test says
otherwise, the snippet passes mypy against 3.6.1 with the repository's settings, and
fails against the typed results of PR #1129. Each test passes once its finding is fixed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import nornir.core
import nornir.core.task
from tests.core.test_operations_typing import check

if TYPE_CHECKING:
    from pathlib import Path

PRELUDE = """
    from nornir.core import Nornir
    from nornir.core.task import AggregatedResult, MultiResult, Result, Task

    def backup(task: Task) -> None:
        pass

    def get_hostname(task: Task) -> str:
        return task.host.name

    def get_version(task: Task) -> dict[str, str]:
        return {"version": "17.9"}
"""

NO_ISSUES = "Success: no issues found"


def test_a_variable_can_hold_runs_of_tasks_with_different_return_types(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def main(nr: Nornir) -> None:
        result = nr.run(task=backup)
        print(result.failed)
        result = nr.run(task=get_hostname)
        print(result.failed)
    """,
    )

    assert NO_ISSUES in report, report


def test_a_subtask_variable_can_hold_subtasks_with_different_return_types(
    tmp_path: Path,
) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def grouped(task: Task) -> None:
        sub = task.run(task=backup)
        sub = task.run(task=get_hostname)
        print(sub.changed)
    """,
    )

    assert NO_ISSUES in report, report


def test_a_list_of_runs_keeps_the_result_attributes(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def main(nr: Nornir) -> None:
        results = [nr.run(task=backup), nr.run(task=get_hostname)]
        for r in results:
            print(r.failed, r.failed_hosts)
        by_name = {"backup": nr.run(task=backup), "hostname": nr.run(task=get_hostname)}
        for r in by_name.values():
            print(r.failed_hosts)
    """,
    )

    assert NO_ISSUES in report, report


def test_the_error_text_of_a_failed_host_can_be_read(tmp_path: Path) -> None:
    # A failed host's result holds the error text, not the task's return type.
    report = check(
        tmp_path,
        PRELUDE
        + """
    def main(nr: Nornir) -> None:
        for _, multi in nr.run(get_version).items():
            if multi.failed:
                print(multi.result.splitlines()[-1])
    """,
    )

    assert NO_ISSUES in report, report


def test_an_optional_result_task_gives_the_value_inside_the_result(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    from typing import Optional

    def maybe(task: Task) -> Optional[Result]:
        if task.host.name == "skip":
            return None
        return Result(task.host, result={"a": 1})

    def main(nr: Nornir) -> None:
        print(nr.run(maybe)["h"].result["a"])
    """,
    )

    assert NO_ISSUES in report, report


def test_an_iterator_generator_task_is_not_typed_as_its_iterator(tmp_path: Path) -> None:
    # Nornir drives the generator; .result is its return value, not the iterator.
    report = check(
        tmp_path,
        PRELUDE
        + """
    from collections.abc import Iterator

    def progress(task: Task) -> Iterator[str]:
        yield "step 1"

    def main(nr: Nornir) -> None:
        print(nr.run(progress)["h"].result["x"])

    def grouped(task: Task) -> None:
        print(task.run(progress).result["x"])
    """,
    )

    assert NO_ISSUES in report, report


def test_a_task_from_a_callable_variable_keeps_an_untyped_result(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    from typing import Callable

    def main(nr: Nornir, tasks: list[Callable[[Task], object]]) -> None:
        for t in tasks:
            print(nr.run(t)["h"].result["x"])
    """,
    )

    assert NO_ISSUES in report, report


def test_a_task_chosen_by_a_condition_keeps_a_usable_result(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def main(nr: Nornir, verbose: bool) -> None:
        print(nr.run(task=get_version if verbose else get_hostname)["h"].result["version"])
    """,
    )

    assert NO_ISSUES in report, report


def test_assigning_the_result_of_a_multi_result_is_rejected(tmp_path: Path) -> None:
    # mypy rejects this against 3.6.1. The assignment does not change multi[0].result,
    # which print_result and processors read.
    report = check(
        tmp_path,
        PRELUDE
        + """
    def fix(multi: MultiResult) -> None:
        multi.result = 5
    """,
    )

    assert NO_ISSUES not in report, report


def test_running_an_async_task_with_a_sync_run_is_rejected(tmp_path: Path) -> None:
    # nr.run raises AsyncTaskOnSyncRunError for this call, before any host runs.
    report = check(
        tmp_path,
        PRELUDE
        + """
    async def aget(task: Task) -> Result:
        return Result(task.host)

    def main(nr: Nornir) -> None:
        nr.run(aget)
    """,
    )

    assert NO_ISSUES not in report, report


def test_the_result_type_variable_is_not_public() -> None:
    # AGENTS.md counts every name without a leading underscore as public API.
    assert not hasattr(nornir.core, "ResultT")
    assert not hasattr(nornir.core.task, "ResultT")
