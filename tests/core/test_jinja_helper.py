from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from nornir.core.helpers.jinja_helper import render_from_file, render_from_string

if TYPE_CHECKING:
    from pathlib import Path


def test_render_from_string_warns_about_deprecation() -> None:
    with pytest.warns(DeprecationWarning, match="nornir_jinja2"):
        result = render_from_string("Hello {{ name }}", name="world")
    assert result == "Hello world"


def test_render_from_file_warns_about_deprecation(tmp_path: Path) -> None:
    template = tmp_path / "hello.j2"
    template.write_text("Hello {{ name }}")

    with pytest.warns(DeprecationWarning, match="nornir_jinja2"):
        result = render_from_file(str(tmp_path), template.name, name="world")
    assert result == "Hello world"
