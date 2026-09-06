"""The implement-phased workflow's shell steps, in one file.

Usage: ``python phased.py <step> <run_id>`` with ``<step>`` one of ``preflight``, ``select``,
``gates``, ``check``, ``final`` or ``summary``, or ``python phased.py agent <name> <run_id>`` to
run one agent step (``implement``, ``judge``, ``fix``, ``review``, ``report``) headless, with the
prompt template ``prompts/<name>.md`` and ``--permission-mode auto``.
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
import string
import subprocess  # noqa: S404  # every argv here is a fixed string from this module
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()


PHASE_HEADING = re.compile(r"^## Phase\s+\S+")
TASK_LINE = re.compile(r"^- \[( |x|X)\] (T\d+)\b")
CHECKPOINT_LINE = re.compile(r"^\*\*Checkpoint\*\*")
CONVENTIONAL_SUBJECT = re.compile(
    r"^(feat|fix|docs|chore|ci|style|refactor|test|perf|build|revert)(\([^)]+\))?!?: \S"
)
PORCELAIN_PATH_OFFSET = 3  # "XY path": two status columns and a space

CONTEXT_CANDIDATES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".specify/memory/constitution.md",
)
SPEC_CANDIDATES = (
    "spec.md",
    "plan.md",
    "tasks.md",
    "research.md",
    "data-model.md",
    "quickstart.md",
)

# Repository quality gates (see AGENTS.md "Commands").
LINT_CMD = "make ruff"
TYPE_CMD = "make mypy"
TEST_CMD = "make pytest"
FULL_CMD = "make tests"

# The agent CLI and the permission mode every agent step runs with. ``auto`` approves routine
# tool calls on its own and denies, rather than prompts, in a headless session.
AGENT_CLI = "claude"
AGENT_PERMISSION_MODE = "auto"
TTY_DEVICE = "CON" if sys.platform == "win32" else "/dev/tty"

MIN_ARGS = 3  # phased.py <step> [<agent>] <run_id>
AGENT_TIMEOUTS = {"implement": 10800, "judge": 1800, "fix": 7200, "review": 3600, "report": 1800}


# ---------------------------------------------------------------- run state


def run_dir(run_id: str) -> Path:
    """Return the engine's run directory for *run_id*.

    Returns:
        ``.specify/workflows/runs/<run_id>`` under the project root.

    """
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        fail(f"Invalid run id {run_id!r}.")
    return ROOT / ".specify" / "workflows" / "runs" / run_id


def state_dir(run_id: str) -> Path:
    """Return (and create) the workflow's own state directory inside the run directory.

    Returns:
        ``<run dir>/phased``.

    """
    d = run_dir(run_id) / "phased"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_inputs(run_id: str) -> dict[str, Any]:
    """Return the resolved workflow inputs persisted by the engine.

    Returns:
        The ``inputs`` mapping from ``inputs.json``, or ``{}`` when absent.

    """
    path = run_dir(run_id) / "inputs.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    inputs = data.get("inputs", data)
    return inputs if isinstance(inputs, dict) else {}


def ledger_path(run_id: str) -> Path:
    """Return the path of the run ledger.

    Returns:
        ``<state dir>/ledger.json``.

    """
    return state_dir(run_id) / "ledger.json"


def load_ledger(run_id: str) -> dict[str, Any]:
    """Return the run ledger, failing when preflight has not created it yet.

    Returns:
        The parsed ledger mapping.

    """
    path = ledger_path(run_id)
    if not path.exists():
        fail("Ledger not found; the preflight step has not run for this run id.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(run_id: str, ledger: dict[str, Any]) -> None:
    """Write the ledger back, stamping ``updated_at``."""
    ledger["updated_at"] = now()
    ledger_path(run_id).write_text(
        json.dumps(ledger, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


def emit(data: dict[str, Any]) -> None:
    """Print the step's JSON output (consumed via ``output_format: json``)."""
    sys.stdout.write(json.dumps(data) + "\n")


def fail(message: str, code: int = 1) -> None:
    """Print *message* to stderr and exit with *code*, failing the shell step."""
    sys.stderr.write(message.rstrip() + "\n")
    sys.exit(code)


def now() -> str:
    """Return the current UTC time as an ISO 8601 string without microseconds.

    Returns:
        For example ``2026-09-06T16:01:02+00:00``.

    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id_arg() -> str:
    """Return the run id, always the last argument.

    Returns:
        ``sys.argv[-1]``.

    """
    if len(sys.argv) < MIN_ARGS or not sys.argv[-1]:
        fail("usage: phased.py <step> [<agent>] <run_id>")
    return sys.argv[-1]


# ----------------------------------------------------------------------- git


def git(*args: str, check: bool = True, strip: bool = True) -> str:
    """Run ``git *args`` in the project root and return its stdout.

    Returns:
        The command's stdout, stripped unless *strip* is false.

    """
    proc = subprocess.run(  # noqa: S603  # argv is built from fixed strings and SHAs
        ["git", *args],  # noqa: S607  # git is resolved from PATH on purpose, like the Makefile
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if check and proc.returncode != 0:
        fail(f"git {' '.join(args)} failed:\n{proc.stderr}")
    return proc.stdout.strip() if strip else proc.stdout


def head_sha() -> str:
    """Return the SHA of ``HEAD``.

    Returns:
        The full 40-character SHA.

    """
    return git("rev-parse", "HEAD")


def dirty_paths(allowed_prefixes: tuple[str, ...]) -> list[str]:
    """Return ``git status --porcelain`` entries whose path is outside *allowed_prefixes*.

    Returns:
        The raw porcelain lines that are not allowed.

    """
    out: list[str] = []
    # Porcelain lines start with the two status columns; do not strip them.
    for line in git("status", "--porcelain", strip=False).splitlines():
        if not line.strip():
            continue
        path = line[PORCELAIN_PATH_OFFSET:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"').replace("\\", "/")
        if any(path.startswith(p) for p in allowed_prefixes):
            continue
        out.append(line)
    return out


def run_shell(cmd: str, timeout: int) -> tuple[int, str]:
    """Run *cmd* through the shell in the project root.

    Returns:
        ``(exit_code, combined stdout and stderr)``; exit code 124 on timeout.

    """
    try:
        proc = subprocess.run(  # noqa: S602  # cmd is one of the fixed gate commands above
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"{cmd}: timed out after {timeout}s"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def tail(text: str, lines: int = 40) -> str:
    """Return the last *lines* lines of *text*.

    Returns:
        The trailing lines joined with newlines.

    """
    parts = text.rstrip().splitlines()
    return "\n".join(parts[-lines:])


# ------------------------------------------------------------------ tasks.md


@dataclass
class Task:
    """One ``- [ ] Txxx`` line of tasks.md."""

    id: str
    done: bool
    line: str


@dataclass
class Group:
    """One ``## Phase N`` section of tasks.md."""

    heading: str
    slug: str
    tasks: list[Task] = field(default_factory=list)
    checkpoint: str = ""
    body: str = ""

    @property
    def ids(self) -> list[str]:
        """Every task id in the group."""
        return [t.id for t in self.tasks]

    @property
    def unticked(self) -> list[str]:
        """The ids of the tasks still marked ``[ ]``."""
        return [t.id for t in self.tasks if not t.done]


def slugify(heading: str) -> str:
    """Return a filesystem-safe slug for a phase heading.

    Returns:
        Lower-case letters, digits and hyphens, at most 60 characters.

    """
    text = heading.lstrip("#").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:60] or "group"


def _close(current: Group | None, body: list[str], groups: list[Group]) -> None:
    if current is not None:
        current.body = "\n".join(body).strip() + "\n"
        groups.append(current)


def parse_tasks(tasks_md: Path) -> list[Group]:
    """Split tasks.md into one group per ``## Phase N`` heading.

    Returns:
        The groups that contain at least one task, in file order.

    """
    groups: list[Group] = []
    current: Group | None = None
    body: list[str] = []
    for raw in tasks_md.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## "):
            _close(current, body, groups)
            current, body = None, []
            if PHASE_HEADING.match(raw):
                current = Group(heading=raw.lstrip("#").strip(), slug=slugify(raw))
                body = [raw]
            continue
        if current is None:
            continue
        body.append(raw)
        m = TASK_LINE.match(raw)
        if m:
            current.tasks.append(Task(id=m.group(2), done=m.group(1) != " ", line=raw))
        elif CHECKPOINT_LINE.match(raw):
            current.checkpoint = raw.strip()
    _close(current, body, groups)
    return [g for g in groups if g.tasks]


def scoped_test_command(group: Group) -> str:
    """Return the pytest command for *group*.

    Prefers the group's own ``make pytest ARGS="..."`` task, then the existing ``tests/`` paths
    its tasks mention, and falls back to the whole suite.

    Returns:
        A shell command string.

    """
    m = re.search(r'make pytest ARGS="([^"]+)"', group.body)
    if m:
        return f'{TEST_CMD} ARGS="{m.group(1)}"'
    paths: list[str] = []
    for mention in re.findall(r"`(tests/[^`\s]+)`", group.body):
        path = mention.split("::", 1)[0]
        if (ROOT / path).exists() and path not in paths:
            paths.append(path)
    if paths:
        return f'{TEST_CMD} ARGS="{" ".join(paths)}"'
    return TEST_CMD


def gate_commands(group: Group) -> list[str]:
    """Return the lint, type and scoped test commands for *group*.

    Returns:
        Three shell command strings.

    """
    return [LINT_CMD, TYPE_CMD, scoped_test_command(group)]


def resolve_spec_dir(inputs: dict[str, Any]) -> Path | None:
    """Return the feature directory: input, then ``.specify/feature.json``, then newest tasks.md.

    Returns:
        An absolute path to a directory, or ``None`` when nothing usable was found.

    """
    raw = str(inputs.get("spec_dir") or "").strip()
    if raw:
        path = (ROOT / raw).resolve()
        return path if path.is_dir() else None
    feature = ROOT / ".specify" / "feature.json"
    if feature.exists():
        try:
            fd = json.loads(feature.read_text(encoding="utf-8")).get("feature_directory")
        except (OSError, ValueError):
            fd = None
        if fd and (ROOT / fd / "tasks.md").exists():
            return (ROOT / fd).resolve()
    candidates = sorted(
        (ROOT / "specs").glob("*/tasks.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    return candidates[0].parent.resolve()


def context_files(spec_dir: Path) -> list[str]:
    """Return the absolute paths of the context files that exist for *spec_dir*.

    Returns:
        Repository documents first, then spec documents, then ``contracts/*``.

    """
    found = [str(ROOT / c) for c in CONTEXT_CANDIDATES if (ROOT / c).exists()]
    found += [str(spec_dir / c) for c in SPEC_CANDIDATES if (spec_dir / c).exists()]
    contracts = spec_dir / "contracts"
    if contracts.is_dir():
        found += [str(p) for p in sorted(contracts.iterdir()) if p.is_file()]
    return found


# Preflight resolves the feature, checks the stop-conditions and seeds the ledger.

MAX_ROUNDS_CAP = 5


def _preflight_max_rounds(inputs: dict[str, Any]) -> int:
    try:
        value = int(float(inputs.get("max_rounds", 3)))
    except (TypeError, ValueError):
        value = 3
    return min(max(value, 1), MAX_ROUNDS_CAP)


def _preflight_new_ledger(
    run_id: str, spec_dir: Path, rel_spec: str, inputs: dict[str, Any]
) -> dict:
    return {
        "run_id": run_id,
        "spec_dir": rel_spec,
        "spec_dir_abs": str(spec_dir),
        "base_sha": head_sha(),
        "started_at": now(),
        "max_rounds": _preflight_max_rounds(inputs),
        "guidance": str(inputs.get("guidance") or ""),
        "context_files": context_files(spec_dir),
        "order": [],
        "groups": {},
        "current": None,
    }


def _preflight_register_groups(ledger: dict, groups: list[Group]) -> None:
    for g in groups:
        if g.slug in ledger["groups"]:
            continue
        ledger["order"].append(g.slug)
        ledger["groups"][g.slug] = {
            "heading": g.heading,
            "task_ids": g.ids,
            "status": "pending" if g.unticked else "done",
            "rounds": 0,
            "start_sha": None,
            "commits": [],
            "findings": [],
            "history": [],
        }


def _preflight_write_overview(path: Path, ledger: dict, groups: list[Group]) -> None:
    lines = [
        f"Feature: {ledger['spec_dir']}",
        f"Base commit: {ledger['base_sha']}",
        f"Validation rounds per group: {ledger['max_rounds']}",
        "",
        "| # | Group | Tasks | Ticked | Status | Gates |",
        "|---|-------|-------|--------|--------|-------|",
    ]
    for i, g in enumerate(groups, 1):
        entry = ledger["groups"][g.slug]
        ticked = len(g.tasks) - len(g.unticked)
        lines.append(
            f"| {i} | {g.heading} | {len(g.tasks)} | {ticked}/{len(g.tasks)} | "
            f"{entry['status']} | {'; '.join(gate_commands(g))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _preflight_stop(run_id: str, headline: str, details: str = "") -> None:
    """Report a stop-condition through the step output so the gate can display it.

    The engine only prints "exited with code N" for a failing shell step, so the message is
    written to a file for the ``preflight-failed`` gate's ``show_file`` and the step exits 0
    with ``ok: false``.
    """
    error_file = state_dir(run_id) / "preflight-error.txt"
    error_file.write_text(headline + ("\n\n" + details if details else "") + "\n", encoding="utf-8")
    emit({"ok": False, "error": headline, "error_file": str(error_file)})
    sys.exit(0)


def _preflight_check_feature(run_id: str, spec_dir: Path, rel_spec: str) -> list[Group]:
    """Verify the spec documents and the working tree; stop the run on any problem.

    Returns:
        The task groups parsed from tasks.md.

    """
    missing = [n for n in ("spec.md", "plan.md", "tasks.md") if not (spec_dir / n).exists()]
    if missing:
        _preflight_stop(
            run_id,
            f"{rel_spec} is missing {', '.join(missing)}.",
            "Run /speckit-specify, /speckit-plan and /speckit-tasks first.",
        )
    groups = parse_tasks(spec_dir / "tasks.md")
    if not groups:
        _preflight_stop(
            run_id, f"{rel_spec}/tasks.md has no '## Phase N' section with '- [ ] Txxx' tasks."
        )
    dirty = dirty_paths((rel_spec + "/", ".specify/"))
    if dirty:
        _preflight_stop(
            run_id,
            "The working tree has changes outside the spec directory; commit or set them aside.",
            "git status --porcelain:\n  " + "\n  ".join(dirty),
        )
    return groups


def cmd_preflight() -> None:
    """Validate the feature and the working tree, then emit the run parameters."""
    run_id = run_id_arg()
    inputs = read_inputs(run_id)
    spec_dir = resolve_spec_dir(inputs)
    if spec_dir is None:
        _preflight_stop(
            run_id,
            f"No usable spec directory (spec_dir input: {inputs.get('spec_dir')!r}).",
            "Pass -i spec_dir=specs/<feature> pointing at a directory that has a tasks.md.",
        )
    assert spec_dir is not None  # noqa: S101  # narrows the type after _preflight_stop() exited
    rel_spec = spec_dir.relative_to(ROOT).as_posix()
    groups = _preflight_check_feature(run_id, spec_dir, rel_spec)
    if shutil.which(AGENT_CLI) is None:
        _preflight_stop(
            run_id,
            f"The {AGENT_CLI!r} CLI is not on PATH; the agent steps cannot run.",
            "Install Claude Code (https://docs.anthropic.com/en/docs/claude-code/setup).",
        )

    ledger = (
        load_ledger(run_id)
        if ledger_path(run_id).exists()
        else _preflight_new_ledger(run_id, spec_dir, rel_spec, inputs)
    )
    _preflight_register_groups(ledger, groups)
    save_ledger(run_id, ledger)
    overview = state_dir(run_id) / "groups.md"
    _preflight_write_overview(overview, ledger, groups)

    emit(
        {
            "ok": True,
            "spec_dir": str(spec_dir),
            "spec_dir_rel": rel_spec,
            "base_sha": ledger["base_sha"],
            "group_count": len(groups),
            "pending": sum(1 for g in groups if g.unticked),
            "max_rounds": ledger["max_rounds"],
            "overview": str(overview),
            "state_dir": str(state_dir(run_id)),
            "context_files": ledger["context_files"],
        }
    )


# Selecting a group picks the next pending phase and writes its self-contained brief.


def _select_pick(groups: list[Group], ledger: dict) -> tuple[Group | None, int]:
    """Find the next group to work on.

    Returns:
        ``(group, remaining)``: the first pending, non-blocked group (or ``None``) and the
        number of pending groups.

    """
    chosen: Group | None = None
    remaining = 0
    for g in groups:
        entry = ledger["groups"].setdefault(
            g.slug,
            {
                "heading": g.heading,
                "task_ids": g.ids,
                "status": "pending",
                "rounds": 0,
                "start_sha": None,
                "commits": [],
                "findings": [],
                "history": [],
            },
        )
        if g.slug not in ledger["order"]:
            ledger["order"].append(g.slug)
        if not g.unticked:
            if entry["status"] not in ("passed", "blocked"):
                entry["status"] = "done"
            continue
        if entry["status"] in ("blocked", "passed"):
            # A blocked group waits for a human; a passed one is never re-opened by this run.
            continue
        remaining += 1
        chosen = chosen or g
    return chosen, remaining


def _select_write_brief(path: Path, group: Group, entry: dict, ledger: dict, state: Path) -> None:
    spec_dir = ledger["spec_dir_abs"]
    evidence = state / "evidence.md"
    text = [
        f"# Group: {group.heading}",
        "",
        f"- Repository root: `{ROOT}`",
        f"- Spec directory: `{spec_dir}`",
        f"- Run state directory: `{state}`",
        f"- Group start commit: `{entry['start_sha']}`",
        f"- Task IDs in scope: {', '.join(group.ids)}",
        f"- Still unticked: {', '.join(group.unticked)}",
        "",
        "## Read first (absolute paths, all exist)",
        "",
        *[f"- `{p}`" for p in ledger["context_files"]],
        "",
        "## Tasks (verbatim from tasks.md)",
        "",
        group.body.rstrip(),
        "",
        "## Acceptance",
        "",
        group.checkpoint
        or "(no checkpoint line in tasks.md; ticked tasks and green gates are the acceptance)",
        "",
        "## Quality gates run by the workflow after you return",
        "",
        *[f"- `{c}`" for c in gate_commands(group)],
        "- every task ID above ticked `[X]` in tasks.md",
        "- `git status` clean: everything committed, Conventional Commits subjects",
        "- no new `# noqa` / `# type: ignore` without a comment saying why",
        "",
        "## Test evidence",
        "",
        f"Append to `{evidence}` one line per new or modified test:",
        (
            "`| <test id as the runner reports it> | <command> | <ISO 8601 pass time> "
            "| <verbatim pass line> |`"
        ),
        (
            "If the group adds or changes no tests, append the line "
            "`no tests added or modified in <group>`."
        ),
    ]
    if ledger.get("guidance"):
        text += ["", "## Guidance from the operator", "", ledger["guidance"]]
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def cmd_select() -> None:
    """Pick the next group, reset its round state, write its brief, and emit the selection."""
    run_id = run_id_arg()
    ledger = load_ledger(run_id)
    spec_dir = Path(ledger["spec_dir_abs"])
    groups = parse_tasks(spec_dir / "tasks.md")
    state = state_dir(run_id)

    chosen, remaining = _select_pick(groups, ledger)
    if chosen is None:
        ledger["current"] = None
        save_ledger(run_id, ledger)
        emit({"found": False, "remaining": 0})
        return

    entry = ledger["groups"][chosen.slug]
    entry["status"] = "in_progress"
    entry["rounds"] = 0
    entry["findings"] = []
    if not entry.get("start_sha"):
        entry["start_sha"] = head_sha()
    ledger["current"] = chosen.slug
    for stale in ("verdict.json", "findings.md", "gates-latest.json"):
        (state / stale).unlink(missing_ok=True)

    brief = state / f"brief-{chosen.slug}.md"
    _select_write_brief(brief, chosen, entry, ledger, state)
    save_ledger(run_id, ledger)

    emit(
        {
            "found": True,
            "heading": chosen.heading,
            "slug": chosen.slug,
            "ids": ", ".join(chosen.ids),
            "brief": str(brief),
            "start_sha": entry["start_sha"],
            "index": ledger["order"].index(chosen.slug) + 1,
            "total": len(ledger["order"]),
            "remaining": remaining,
            "gates": "; ".join(gate_commands(chosen)),
        }
    )


# The mechanical gate checks checkboxes, commits, the tree, the repo gates and the diff.

IGNORE_MARKER = re.compile(r"#\s*(noqa|type:\s*ignore)")
JUSTIFIED = re.compile(r"#\s*(noqa|type:\s*ignore)[^#]*#\s*\S")
GATE_TIMEOUT = 3000


def _gates_bookkeeping(group: Group, start: str) -> tuple[list[str], list[str]]:
    """Check checkboxes, commits, subjects and tree state.

    Returns:
        ``(failures, commits)``: human-readable failures and the SHAs since *start*.

    """
    failures: list[str] = []
    if group.unticked:
        failures.append(f"tasks.md still has unticked tasks: {', '.join(group.unticked)}")
    commits = [c for c in git("rev-list", "--reverse", f"{start}..HEAD").splitlines() if c]
    if not commits:
        failures.append("no commit since the group started; the work must be committed")
    subjects = git("log", "--format=%s", f"{start}..HEAD").splitlines() if commits else []
    bad = [s for s in subjects if not CONVENTIONAL_SUBJECT.match(s)]
    if bad:
        failures.append("commit subjects not Conventional Commits: " + " | ".join(bad))
    dirty = dirty_paths((".specify/",))
    if dirty:
        failures.append("working tree not clean:\n    " + "\n    ".join(dirty))
    return failures, commits


def _gates_unjustified_ignores(start: str) -> list[str]:
    """Scan the group diff for unexplained ignores.

    Returns:
        One failure string per added line carrying ``noqa`` / ``type: ignore`` and no comment.

    """
    diff = git("diff", "-U0", f"{start}..HEAD", "--", "*.py", check=False)
    return [
        "new lint/type ignore without a justifying comment: " + line[1:].strip()
        for line in diff.splitlines()
        if line.startswith("+")
        and not line.startswith("+++")
        and IGNORE_MARKER.search(line)
        and not JUSTIFIED.search(line)
    ]


def _gates_run_round(group: Group, start: str, round_no: int, log: Path) -> dict:
    """Run the bookkeeping checks and the gate commands, writing the log file.

    Returns:
        The ``gates-latest.json`` payload.

    """
    failures, commits = _gates_bookkeeping(group, start)
    sections = [f"# Gates for {group.heading} (round {round_no}) at {now()}", ""]
    for cmd in gate_commands(group):
        code, out = run_shell(cmd, timeout=GATE_TIMEOUT)
        sections += [f"## $ {cmd}  (exit {code})", "", out.rstrip(), ""]
        if code != 0:
            failures.append(f"`{cmd}` exited {code}:\n" + tail(out, 30))
    if commits:
        failures += _gates_unjustified_ignores(start)
    verdict = "PASS" if not failures else "FAIL"
    sections += ["## Result", "", verdict, *[f"- {f}" for f in failures]]
    log.write_text("\n".join(sections) + "\n", encoding="utf-8")
    return {
        "passed": not failures,
        "failures": failures,
        "commits": commits,
        "log": str(log),
        "round": round_no,
        "at": now(),
    }


def cmd_gates() -> None:
    """Run every mechanical check for the current group and record the result."""
    run_id = run_id_arg()
    ledger = load_ledger(run_id)
    slug = ledger.get("current")
    if not slug:
        fail("No current group; select-group has not run.")
    entry = ledger["groups"][slug]
    spec_dir = Path(ledger["spec_dir_abs"])
    group = next((g for g in parse_tasks(spec_dir / "tasks.md") if g.slug == slug), None)
    if group is None:
        fail(f"Group {slug!r} no longer exists in tasks.md.")
    assert group is not None  # noqa: S101  # narrows the type after fail() exited
    state = state_dir(run_id)
    round_no = int(entry.get("rounds", 0)) + 1
    start = entry.get("start_sha") or ledger["base_sha"]
    result = _gates_run_round(group, start, round_no, state / f"gates-{slug}-r{round_no}.log")
    (state / "gates-latest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (state / "verdict.json").unlink(missing_ok=True)
    save_ledger(run_id, ledger)
    emit(
        {
            "passed": result["passed"],
            "failures": len(result["failures"]),
            "log": result["log"],
            "round": round_no,
            "start_sha": start,
            "heading": group.heading,
        }
    )


# Checking a round merges the gate result and the judge verdict into pass, retry or blocked.


def _check_format_finding(item: Any) -> str:
    if not isinstance(item, dict):
        return f"[judge] {item}"
    loc = str(item.get("file", "?"))
    if item.get("line"):
        loc += f":{item['line']}"
    return f"[judge] {loc} — {item.get('criterion', '')}: {item.get('summary', '')}".strip()


def _check_judge_findings(verdict_path: Path) -> tuple[list[str], str]:
    """Read the judge's verdict file.

    Returns:
        ``(findings, label)``: formatted findings (empty on PASS) and the verdict label.

    """
    if not verdict_path.exists():
        return ["the judge did not write verdict.json; treat as FAIL"], "missing"
    try:
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"verdict.json is not valid JSON: {exc}"], "invalid"
    label = str(verdict.get("verdict", "")).upper()
    if label == "PASS":
        return [], label
    items = verdict.get("findings") or []
    if not items:
        return ["judge verdict FAIL without findings"], label or "FAIL"
    return [_check_format_finding(f) for f in items], label or "FAIL"


def _check_write_findings(
    path: Path, entry: dict, gates: dict, round_no: int, max_rounds: int
) -> None:
    passed = entry["status"] == "passed"
    exhausted = entry["status"] == "blocked"
    outcome = "PASS" if passed else ("BLOCKED (round cap reached)" if exhausted else "FAIL")
    lines = [
        f"# Findings for {entry['heading']} — round {round_no} of {max_rounds}",
        "",
        f"Outcome: {outcome}",
        f"Gate log: {gates.get('log', '')}",
        "",
        *[f"{i}. {f}" for i, f in enumerate(entry["findings"], 1)],
    ]
    if not entry["findings"]:
        lines.append("No findings.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_check() -> None:
    """Decide whether the current group passed, needs another round, or is blocked."""
    run_id = run_id_arg()
    ledger = load_ledger(run_id)
    slug = ledger.get("current")
    if not slug:
        fail("No current group; select-group has not run.")
    entry = ledger["groups"][slug]
    state = state_dir(run_id)
    max_rounds = int(ledger.get("max_rounds", 3))

    gates_path = state / "gates-latest.json"
    gates: dict = (
        json.loads(gates_path.read_text(encoding="utf-8"))
        if gates_path.exists()
        else {"passed": False, "failures": ["gates did not run"], "commits": [], "log": ""}
    )
    findings: list[str] = list(gates.get("failures", []))
    judge_label = "n/a"
    if gates.get("passed"):
        judge_findings, judge_label = _check_judge_findings(state / "verdict.json")
        findings += judge_findings

    passed = not findings
    round_no = int(entry.get("rounds", 0)) + 1
    exhausted = round_no >= max_rounds
    entry["rounds"] = round_no
    entry["findings"] = findings
    entry["history"].append(
        {
            "round": round_no,
            "passed": passed,
            "gates_passed": bool(gates.get("passed")),
            "judge": judge_label,
            "findings": len(findings),
            "at": now(),
        }
    )
    if passed:
        entry["status"] = "passed"
        entry["commits"] = gates.get("commits", [])
        entry["passed_at"] = now()
    elif exhausted:
        entry["status"] = "blocked"

    findings_md = state / "findings.md"
    _check_write_findings(findings_md, entry, gates, round_no, max_rounds)
    save_ledger(run_id, ledger)
    emit(
        {
            "passed": passed,
            "retry": (not passed) and (not exhausted),
            "exhausted": exhausted,
            "round": round_no,
            "max_rounds": max_rounds,
            "findings": str(findings_md),
            "finding_count": len(findings),
            "heading": entry["heading"],
        }
    )


# The final gate runs the whole repository gate once over the complete change set.

FULL_TIMEOUT = 3600


def cmd_final() -> None:
    """Run ``make tests``, record ``docs/api`` drift, and store the outcome in the ledger."""
    run_id = run_id_arg()
    ledger = load_ledger(run_id)
    log = state_dir(run_id) / "final-gates.log"
    failures: list[str] = []
    code, out = run_shell(FULL_CMD, timeout=FULL_TIMEOUT)
    if code != 0:
        failures.append(f"`{FULL_CMD}` exited {code}:\n" + tail(out, 40))
    dirty = dirty_paths((".specify/",))
    if dirty:
        failures.append("working tree not clean after the full gate:\n    " + "\n    ".join(dirty))
    api_changed = git(
        "diff", "--name-only", f"{ledger['base_sha']}..HEAD", "--", "docs/api", check=False
    ).splitlines()
    result = "PASS" if not failures else "FAIL\n" + "\n".join(f"- {f}" for f in failures)
    log.write_text(
        f"# {FULL_CMD} at {now()} (exit {code})\n\n{out}\n\n"
        "## docs/api files changed since base\n"
        + ("\n".join(api_changed) or "(none)")
        + f"\n\n## Result\n{result}\n",
        encoding="utf-8",
    )
    ledger["final_gates"] = {
        "passed": not failures,
        "log": str(log),
        "docs_api_changed": api_changed,
        "at": now(),
    }
    save_ledger(run_id, ledger)
    emit({"passed": not failures, "log": str(log), "docs_api_changed": len(api_changed)})


# The summary writes summary.txt with the STATUS line the report agent prints last.


def cmd_summary() -> None:
    """Summarise the ledger and tasks.md into summary.txt and the ledger's final status."""
    run_id = run_id_arg()
    ledger = load_ledger(run_id)
    spec_dir = Path(ledger["spec_dir_abs"])
    groups = parse_tasks(spec_dir / "tasks.md")
    unticked = [t for g in groups for t in g.unticked]
    entries = [ledger["groups"][s] for s in ledger["order"]]
    passed = sum(1 for e in entries if e["status"] in ("passed", "done"))
    blocked = [e["heading"] for e in entries if e["status"] == "blocked"]
    final = ledger.get("final_gates", {})
    done = not unticked and not blocked and bool(final.get("passed"))

    reasons: list[str] = []
    if blocked:
        reasons.append(f"{len(blocked)} blocked group(s): {'; '.join(blocked)}")
    if unticked:
        reasons.append(f"{len(unticked)} task(s) still unticked")
    if not final.get("passed"):
        reasons.append("full gate not green")
    status = "DONE" if done else "INCOMPLETE"
    reason = "; ".join(reasons) or "n/a"

    lines = [
        f"Feature:        {ledger['spec_dir']}",
        f"Commits:        {ledger['base_sha'][:12]}..{head_sha()[:12]}",
        f"Groups:         {passed}/{len(entries)} passed, {len(blocked)} blocked",
        f"Open tasks:     {len(unticked)}",
        f"Full gate:      {'green' if final.get('passed') else 'red or not run'}",
        f"STATUS: {status} | SPEC_DIR: {spec_dir} | REASON: {reason}",
    ]
    out = state_dir(run_id) / "summary.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ledger["status"] = status
    ledger["reasons"] = reasons
    save_ledger(run_id, ledger)
    emit(
        {
            "status": status,
            "summary": str(out),
            "blocked": len(blocked),
            "open_tasks": len(unticked),
            "reason": reason,
        }
    )


# The agent step renders a prompt template and runs the agent CLI headless with auto permissions.


def _agent_context(run_id: str, ledger: dict[str, Any]) -> dict[str, str]:
    """Collect every placeholder the prompt templates may use from the run state.

    Returns:
        A mapping of placeholder name to value; unknown state yields ``"n/a"``.

    """
    state = state_dir(run_id)
    slug = ledger.get("current") or ""
    entry = ledger["groups"].get(slug, {})
    gates_path = state / "gates-latest.json"
    gates = json.loads(gates_path.read_text(encoding="utf-8")) if gates_path.exists() else {}
    order = ledger.get("order", [])
    return {
        "spec_dir": ledger["spec_dir_abs"],
        "state_dir": str(state),
        "base_sha": ledger["base_sha"],
        "brief": str(state / f"brief-{slug}.md"),
        "heading": entry.get("heading", "n/a"),
        "ids": ", ".join(entry.get("task_ids", [])),
        "index": str(order.index(slug) + 1 if slug in order else 0),
        "total": str(len(order)),
        "start_sha": entry.get("start_sha") or ledger["base_sha"],
        "gates_log": str(gates.get("log", "n/a")),
        "round": str(entry.get("rounds", 0)),
        "findings": str(state / "findings.md"),
        "final_log": str(ledger.get("final_gates", {}).get("log", "n/a")),
        "summary": str(state / "summary.txt"),
        "status": str(ledger.get("status", "n/a")),
    }


def _show(text: str) -> None:
    """Echo the agent's final message on the terminal, if there is one.

    The shell step captures stdout, so this writes to the controlling terminal directly and
    stays silent when there is none (CI, ``--json`` piped runs).
    """
    with contextlib.suppress(OSError):
        Path(TTY_DEVICE).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def cmd_agent() -> None:
    """Run one agent step: ``phased.py agent <implement|judge|fix|review|report> <run_id>``."""
    name = sys.argv[2] if len(sys.argv) > MIN_ARGS else ""
    if name not in AGENT_TIMEOUTS:
        fail(f"usage: phased.py agent <{'|'.join(AGENT_TIMEOUTS)}> <run_id>")
    run_id = run_id_arg()
    ledger = load_ledger(run_id)
    template = Path(__file__).parent / "prompts" / f"{name}.md"
    prompt = string.Template(template.read_text(encoding="utf-8")).safe_substitute(
        _agent_context(run_id, ledger)
    )
    model = str(read_inputs(run_id).get("model") or "opus")
    log = state_dir(run_id) / f"agent-{name}-{now().replace(':', '')}.log"
    argv = [
        shutil.which(AGENT_CLI) or AGENT_CLI,
        "-p",
        prompt,
        "--permission-mode",
        AGENT_PERMISSION_MODE,
        "--model",
        model,
    ]
    started = now()
    try:
        proc = subprocess.run(  # noqa: S603  # argv is fixed apart from the rendered prompt
            argv,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=AGENT_TIMEOUTS[name],
            check=False,
        )
        exit_code, output = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        output = f"{AGENT_CLI} timed out after {exc.timeout}s\n" + str(exc.stdout or "")
    except OSError as exc:
        exit_code, output = 127, f"could not start {AGENT_CLI}: {exc}\n"
    log.write_text(
        f"# agent {name} | model {model} | started {started} | exit {exit_code}\n\n{output}",
        encoding="utf-8",
    )
    _show(f"\n--- agent {name} ({model}) exit {exit_code} ---\n{output.strip()}\n")
    ledger.setdefault("agents", []).append(
        {"step": name, "model": model, "started": started, "exit_code": exit_code, "log": str(log)}
    )
    save_ledger(run_id, ledger)
    # A failed agent is not a failed run: the next mechanical gate decides what is missing.
    emit({"agent": name, "model": model, "exit_code": exit_code, "log": str(log)})


STEPS = {
    "agent": cmd_agent,
    "preflight": cmd_preflight,
    "select": cmd_select,
    "gates": cmd_gates,
    "check": cmd_check,
    "final": cmd_final,
    "summary": cmd_summary,
}


def main() -> None:
    """Dispatch ``python phased.py <step> <run_id>``."""
    if len(sys.argv) < MIN_ARGS or sys.argv[1] not in STEPS:
        fail(f"usage: phased.py <{'|'.join(STEPS)}> [<agent>] <run_id>")
    STEPS[sys.argv[1]]()


if __name__ == "__main__":
    main()
