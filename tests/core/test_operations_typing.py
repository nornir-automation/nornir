"""Type errors the caller of an Operation must see, checked by running mypy on snippets."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

mypy_api = pytest.importorskip("mypy.api")

ROOT = Path(__file__).resolve().parents[2]


def check(tmp_path: Path, code: str) -> str:
    """Type-check ``code`` with the repository's mypy settings.

    Returns:
        The report of mypy.

    """
    snippet = tmp_path / "snippet.py"
    snippet.write_text(textwrap.dedent(code), encoding="utf-8")
    report, errors, _ = mypy_api.run(
        ["--config-file", str(ROOT / "pyproject.toml"), "--no-incremental", str(snippet)]
    )
    return str(report) + str(errors)


PRELUDE = """
    from nornir.core import Nornir
    from tests.core.operations_helpers import GetConfig, GetConfigInput
"""


def test_a_params_callable_returning_the_wrong_type_is_rejected(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def run(nr: Nornir) -> None:
        nr.run_operation(GetConfig, lambda host: 3)
    """,
    )

    assert 'Incompatible return value type (got "int", expected "GetConfigInput")' in report


def test_reading_a_missing_output_field_is_rejected(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    def run(nr: Nornir) -> None:
        for res in nr.run_operation(GetConfig).results():
            res.result.configuration
    """,
    )

    assert '"GetConfigOutput" has no attribute "configuration"' in report


def test_an_input_of_another_model_is_rejected(tmp_path: Path) -> None:
    report = check(
        tmp_path,
        PRELUDE
        + """
    from tests.core.operations_helpers import BackupInput

    def run(nr: Nornir) -> None:
        nr.run_operation(GetConfig, BackupInput(path="/b"))
    """,
    )

    assert "No overload variant" in report or "incompatible type" in report
