from pathlib import Path

import pytest

from tests.wheel_importability import find_built_wheel, find_environment_python


def test_find_built_wheel_returns_the_only_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "nornir-3.6.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")

    assert find_built_wheel(tmp_path) == wheel


def test_find_built_wheel_rejects_missing_wheel(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r"exactly one wheel.*found 0"):
        find_built_wheel(tmp_path)


def test_find_built_wheel_rejects_multiple_wheels(tmp_path: Path) -> None:
    (tmp_path / "first.whl").write_bytes(b"first")
    (tmp_path / "second.whl").write_bytes(b"second")

    with pytest.raises(RuntimeError, match=r"exactly one wheel.*found 2"):
        find_built_wheel(tmp_path)


def test_find_environment_python_supports_posix_layout(tmp_path: Path) -> None:
    python = tmp_path / "bin" / "python"
    python.parent.mkdir()
    python.touch()

    assert find_environment_python(tmp_path) == python


def test_find_environment_python_supports_windows_layout(tmp_path: Path) -> None:
    python = tmp_path / "Scripts" / "python.exe"
    python.parent.mkdir()
    python.touch()

    assert find_environment_python(tmp_path) == python


def test_find_environment_python_rejects_unknown_layout(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Unable to find Python"):
        find_environment_python(tmp_path)
