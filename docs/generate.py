"""Generate the Markdown pages Docusaurus builds from but that are not committed.

Two kinds of content are derived from other sources at build time:

* every Jupyter notebook under ``docs/docs`` is rendered to a sibling ``<name>.ipynb.md`` file,
  so the notebooks stay the single source of truth that ``make nbval`` verifies, and
* the API reference under ``docs/docs/api`` is rendered from the ``nornir`` package docstrings
  with `mdxify <https://github.com/zzstoatzz/mdxify>`_.

Both outputs are gitignored. Run this script (``make docs-generate``) before ``npm start`` or
``npm run build``.
"""

import argparse
import json
import logging
import re
import shutil
import subprocess  # noqa: S404 - mdxify is run as a child process with a fixed argv
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import nbformat

logger = logging.getLogger("docs.generate")

DOCS_ROOT = Path(__file__).resolve().parent
CONTENT_DIR = DOCS_ROOT / "docs"
API_DIR = CONTENT_DIR / "api"
REPO_URL = "https://github.com/nornir-automation/nornir"
NOTEBOOK_SUFFIX = ".ipynb.md"

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HIGHLIGHT_FILE_MAGIC = re.compile(r"^%highlight_file\s+(\S+)\s*$")
CAT_MAGIC = re.compile(r"^%cat\s+(\S+)\s*$")
# Sphinx cross-reference roles, such as :obj:`nornir.core.Nornir.run`, have no meaning outside
# Sphinx. mdxify escapes the colons in some positions, hence the optional backslashes.
SPHINX_ROLE = re.compile(r":?(?:py\\?:)?(?:obj|meth|class|func|attr|exc|mod|data)\\?:(?=`)")
API_HEADING = re.compile(r"^(###|####) `(\w+)`")
SUFFIX_LANGUAGES = {".yaml": "yaml", ".yml": "yaml", ".json": "json", ".py": "python"}


class DocsGenerationError(Exception):
    """Raised when a source cannot be rendered into a documentation page."""


def fence(body: str, language: str = "", title: str | None = None) -> str:
    """Wrap text in a Markdown code fence long enough not to clash with its content.

    Args:
        body: Text to put inside the fence.
        language: Prism language name for syntax highlighting.
        title: Optional title shown above the block by Docusaurus.

    Returns:
        The fenced block, without a trailing newline.

    """
    longest_run = max((len(run) for run in re.findall(r"`+", body)), default=0)
    ticks = "`" * max(3, longest_run + 1)
    info = language + (f' title="{title}"' if title else "")
    return f"{ticks}{info}\n{body.rstrip()}\n{ticks}"


def render_outputs(outputs: list[Any], language: str, notebook: Path) -> Iterator[str]:
    """Render the stored outputs of a code cell as fenced text blocks.

    Args:
        outputs: The ``outputs`` list of an nbformat code cell.
        language: Language used to highlight stream output.
        notebook: The notebook being rendered, for error messages.

    Yields:
        One fenced block per output.

    Raises:
        DocsGenerationError: If an output has no plain text representation.

    """
    for output in outputs:
        if output.output_type == "stream":
            yield fence(ANSI_ESCAPE.sub("", output.text), language)
        elif output.output_type == "error":
            yield fence(ANSI_ESCAPE.sub("", "\n".join(output.traceback)), "text")
        elif "text/plain" in output.get("data", {}):
            yield fence(output.data["text/plain"], "text")
        else:
            mime_types = ", ".join(output.get("data", {})) or output.output_type
            raise DocsGenerationError(f"{notebook}: cannot render output of type {mime_types}")


def render_code_cell(cell: Any, notebook: Path) -> Iterator[str]:
    """Render a code cell and its stored outputs.

    ``%run`` cells only load helpers and are dropped. ``%highlight_file`` produces pygments
    HTML, so the referenced file is shown as a titled code block instead.

    Args:
        cell: An nbformat code cell.
        notebook: The notebook being rendered.

    Yields:
        Markdown blocks for the cell.

    """
    source = cell.source.strip()
    statements = [line for line in source.splitlines() if not line.lstrip().startswith("#")]
    if not statements or all(line.startswith("%run ") for line in statements):
        return
    if len(statements) == 1 and (highlight := HIGHLIGHT_FILE_MAGIC.match(statements[0])):
        shown = notebook.parent / highlight.group(1)
        language = SUFFIX_LANGUAGES.get(shown.suffix, "text")
        yield fence(shown.read_text(encoding="utf-8"), language, title=highlight.group(1))
        return
    yield fence(source, "python")
    cat = CAT_MAGIC.match(statements[0]) if len(statements) == 1 else None
    output_language = SUFFIX_LANGUAGES.get(Path(cat.group(1)).suffix, "text") if cat else "text"
    yield from render_outputs(cell.outputs, output_language, notebook)


def front_matter(fields: dict[str, str | None]) -> str:
    """Render a YAML front matter block, using JSON quoting so values never need escaping.

    Args:
        fields: Front matter keys and values. ``None`` renders as YAML ``null``.

    Returns:
        The front matter block, including the ``---`` delimiters.

    """
    lines = [f"{key}: {json.dumps(value)}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---"


def promote_first_heading(blocks: list[str]) -> str:
    """Make the first heading a level-one heading and return its text.

    Some notebooks open with ``## Title``; Docusaurus uses the first ``#`` heading as the page
    title, so the first heading is promoted.

    Args:
        blocks: Rendered Markdown blocks, modified in place.

    Returns:
        The title text.

    Raises:
        DocsGenerationError: If no block starts with a heading.

    """
    for index, block in enumerate(blocks):
        first_line, _, rest = block.partition("\n")
        if heading := HEADING.match(first_line):
            blocks[index] = f"# {heading.group(2)}\n{rest}".rstrip()
            return heading.group(2)
    raise DocsGenerationError("notebook has no heading to use as page title")


def render_notebook(notebook: Path) -> Path:
    """Render one notebook to a sibling ``.ipynb.md`` page.

    Args:
        notebook: Path of the notebook.

    Returns:
        Path of the generated page.

    Raises:
        DocsGenerationError: If the notebook has no heading to use as title.

    """
    contents = nbformat.read(notebook, as_version=4)
    blocks: list[str] = []
    for cell in contents.cells:
        if cell.cell_type == "markdown":
            blocks.append(cell.source.strip())
        elif cell.cell_type == "code":
            blocks.extend(render_code_cell(cell, notebook))
    try:
        title = promote_first_heading(blocks)
    except DocsGenerationError as error:
        raise DocsGenerationError(f"{notebook}: {error}") from error
    source = notebook.relative_to(DOCS_ROOT.parent).as_posix()
    header = front_matter(
        {
            "id": notebook.stem,
            "title": title,
            "custom_edit_url": f"{REPO_URL}/blob/main/{source}",
        }
    )
    comment = f"<!-- Generated from {notebook.name} by docs/generate.py. Do not edit. -->"
    page = notebook.with_name(notebook.stem + NOTEBOOK_SUFFIX)
    page.write_text("\n\n".join([header, comment, *blocks]) + "\n", encoding="utf-8")
    return page


def generate_notebooks() -> None:
    """Render every notebook under the content directory, removing stale pages first."""
    for stale in CONTENT_DIR.rglob(f"*{NOTEBOOK_SUFFIX}"):
        stale.unlink()
    for notebook in sorted(CONTENT_DIR.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in notebook.parts:
            continue
        page = render_notebook(notebook)
        logger.info("rendered %s", page.relative_to(DOCS_ROOT))


def anchor_api_headings(body: str) -> str:
    """Give every class, method and function heading an explicit, Python-style anchor.

    Docusaurus would otherwise slug ``### `Task` <sup>...`` to ``task-`` and number repeated
    method names. Explicit anchors such as ``#Task`` and ``#Nornir.run`` are stable and
    unambiguous within a module page.

    Args:
        body: Page body produced by mdxify.

    Returns:
        The body with ``{#anchor}`` appended to symbol headings.

    """
    lines = []
    section = owner = ""
    for line in body.splitlines():
        if line.startswith("## "):
            section, owner = line[3:].strip(), ""
        elif symbol := API_HEADING.match(line):
            level, name = symbol.groups()
            if level == "###":
                anchor = name
                owner = name if section == "Classes" else ""
            else:
                anchor = f"{owner}.{name}" if owner else name
            line = f"{line} {{#{anchor}}}"  # noqa: PLW2901 - rewriting the line is the point
        lines.append(line)
    return "\n".join(lines)


def clean_api_page(text: str, module: str) -> str:
    """Adapt an mdxify page to Docusaurus.

    Replaces mdxify's Mintlify front matter, strips Sphinx roles from docstrings and marks the
    page as generated.

    Args:
        text: Page produced by mdxify.
        module: Dotted name of the documented module.

    Returns:
        The cleaned page.

    Raises:
        DocsGenerationError: If the page does not start with front matter.

    """
    if not text.startswith("---\n"):
        raise DocsGenerationError(f"mdxify page for {module} has no front matter")
    _, _, body = text[4:].partition("\n---\n")
    header = front_matter({"title": module, "sidebar_label": module, "custom_edit_url": None})
    comment = "{/* Generated from the nornir docstrings by docs/generate.py. Do not edit. */}"
    return f"{header}\n\n{comment}\n{anchor_api_headings(SPHINX_ROLE.sub('', body))}\n"


def generate_api() -> None:
    """Render the API reference for the ``nornir`` package with mdxify.

    Raises:
        DocsGenerationError: If mdxify fails.

    """
    with tempfile.TemporaryDirectory() as scratch:
        command = [
            sys.executable, "-m", "mdxify", "--all", "--root-module", "nornir",
            "--output-dir", scratch, "--no-update-nav", "--format", "mdx",
            "--docstring-style", "google", "--repo-url", REPO_URL, "--branch", "main",
        ]  # fmt: skip
        result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv, no user input
        if result.returncode != 0:
            raise DocsGenerationError(f"mdxify failed:\n{result.stdout}\n{result.stderr}")
        shutil.rmtree(API_DIR, ignore_errors=True)
        API_DIR.mkdir(parents=True)
        for generated in sorted(Path(scratch).glob("*.mdx")):
            stem = generated.stem.removesuffix("-__init__")
            module = stem.replace("-", ".")
            page = API_DIR / f"{stem}.mdx"
            page.write_text(
                clean_api_page(generated.read_text(encoding="utf-8"), module), encoding="utf-8"
            )
            logger.info("rendered %s", page.relative_to(DOCS_ROOT))


def main() -> int:
    """Parse arguments and generate the requested content.

    Returns:
        Process exit code.

    """
    parser = argparse.ArgumentParser(description="Generate notebook and API pages.")
    parser.add_argument("target", choices=["all", "notebooks", "api"], nargs="?", default="all")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        if arguments.target in {"all", "notebooks"}:
            generate_notebooks()
        if arguments.target in {"all", "api"}:
            generate_api()
    except DocsGenerationError:
        logger.exception("documentation generation failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
