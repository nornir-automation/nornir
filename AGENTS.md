# AGENTS.md

Portable instructions for AI coding agents working in this repository. This is the single
source of truth; `CLAUDE.md` imports it and adds only Claude-specific overrides.

## What Nornir is

Nornir is a pure-Python automation framework: a library you drive *from* Python rather than a
runtime you configure with a DSL. It owns three things — inventory modelling, task dispatch and
concurrency, and the plugin registry. Everything that talks to a specific device, vendor, or
protocol lives in a separate package discovered through `nornir.plugins.*` entry points; plugins
have shipped out of tree since 3.0.0.

The practical consequence for every change: a user must be able to drop
`import pdb; pdb.set_trace()` into a task and step straight through it, and tracebacks must point
at real user code. Anything that puts an interpreter layer between the user and their own
functions is the wrong direction for this project.

## Governing documents

Read these rather than inferring the rules from the code:

- `.specify/memory/constitution.md` — the six ratified principles plus the quality-gate and
  workflow sections. This is the authority; where any other document conflicts with it, it wins
  and the other one is to be corrected.
- `CONTRIBUTING.rst` — contributor-facing workflow (environment setup, dependency policy, tests).
  Also rendered as the docs' contributing page.
- `CHANGELOG.rst` — user-visible history; every user-visible change adds an entry here.

One known drift, so you do not "fix" the wrong side of it: both the constitution and
`CONTRIBUTING.rst` state that development dependencies are unpinned (`*`) with `ruff` alone pinned
exactly, but `pyproject.toml` currently uses ranges (`ruff>=0.15.20,<0.16`, `mypy>=1.5.1,<2`) and
pins the nornir plugin packages exactly. The policy is the stated one; whether the pins or the
policy changes has not been decided, so do not quietly "correct" either to match the other.

## Repository map

```text
nornir/core/          inventory, task dispatch, config, plugin registry — the actual core
nornir/core/plugins/  the plugin Protocol contracts and the registry
nornir/plugins/       the only in-tree reference plugins: SimpleInventory, SerialRunner,
                      ThreadedRunner. Adding another needs maintainer approval.
tests/                pytest suite, mirroring the package layout; YAML fixtures alongside
docs/tutorial/        learning-oriented notebooks (executed in CI)
docs/howto/           task-oriented notebooks and guides (executed in CI)
docs/api/             Sphinx API reference — GENERATED, see Gotchas
docs/upgrading/       major-version upgrade guides
.agents/              agent-facing source of truth: skills/, commands/, rules/
.claude/              Claude adapter; skills/commands/rules are symlink views of .agents/
.specify/             Spec Kit engine (specify -> plan -> tasks -> implement)
```

## Commands

`uv` is the only supported environment manager. Set up with `uv sync --locked`.

| Command | What it does |
|---|---|
| `make tests` | The authoritative gate: `ruff`, `mypy`, `nbval`, `pytest`, `docs`. All five must pass. |
| `make pytest` | Unit tests with coverage. Fastest useful loop; run this first. |
| `make mypy` | Type-checks `nornir` and `tests`. |
| `make ruff` | Lints (`ruff check .`). Format separately with `uv run ruff format .`. |
| `make nbval` | Re-executes the documentation notebooks and verifies their stored output. |
| `make docs` | Regenerates the API reference, then builds Sphinx HTML. |
| `make docker-tests` | Runs the whole suite in the CI Linux image. |

Supported Python is 3.10 through 3.14, on Linux, macOS, and Windows. All three platforms are
first-class in CI.

## Conventions that actually bite

**Typing is not optional.** New and modified code carries complete annotations and passes mypy
under the strict settings in `[tool.mypy]` (`disallow_untyped_defs`, `disallow_any_generics`,
`disallow_untyped_calls`, `warn_return_any`, …). Do not reach for `# type: ignore` where a real
fix exists.

**The ruff ignore list is a debt ledger, not a licence.** `pyproject.toml` selects `ALL` and then
ignores a long list under a banner saying the entries "should be removed once the code has been
updated". Removing entries is welcome. Adding one requires a comment saying why. Same for
`# noqa`.

**Tests are part of the change.** A bug fix includes a test that fails before the fix and passes
after it. If something genuinely cannot be exercised on a platform, say so explicitly in the pull
request instead of skipping quietly.

**Notebook output must be real.** The notebooks under `docs/tutorial/` and `docs/howto/` are
executed by `make nbval` and their stored output is compared against the run. Never hand-write,
trim, or tidy notebook output — re-execute the notebook and commit what it actually produced.
Output that varies run to run is normalised in `docs/nbval_sanitize.cfg`.

**Public API changes are breaking changes.** The public surface is everything importable from
`nornir` without a leading underscore, plus the `ConnectionPlugin`, `InventoryPlugin`,
`RunnerPlugin`, `Processor`, and `TransformFunction` contracts. These are `typing.Protocol`
definitions, so third-party plugins satisfy them structurally — changing a signature breaks every
conforming plugin at once, with no inheritance error anywhere to catch it. Treat any signature
change as breaking, ship it in a MAJOR release with a guide under `docs/upgrading/`, and give
deprecations at least one MINOR release of warnings first.

**Windows is a real target.** Do not assume POSIX path separators, unlimited path lengths, or
shell semantics.

## Gotchas

- `docs/api/nornir/**` is **generated** by `docs/build_api.sh`, which deletes and rewrites the
  tree — but the result is committed. Adding or removing a module under `nornir/` therefore
  changes tracked files: run `make docs` and commit what it regenerates. Never hand-edit those
  `.rst` files.
- `docs/configuration/generated/` is gitignored; `docs/configuration/parameters.rst` is not.
- The core takes no new runtime dependency to serve a single plugin's use case. Runtime deps live
  in `[project.dependencies]` and are currently just `ruamel.yaml`.
- `PYTHON:=3.10` in the `Makefile` is the Docker build argument, not the project's target version.

## Workflow

`main` is the integration branch and the target for pull requests. Nobody commits directly to
`main` or a release branch. Work happens on a branch named for its intent (`feat/`, `fix/`,
`docs/`, `chore/`, `refactor/`) or under a contributor-scoped prefix (`dga/…`); both are in use.

Significant core changes need a tracking GitHub issue before the pull request **merges** — early
is better, but it is not a precondition for writing code. Prototype first if the prototype is
what makes the design arguable.

Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `style:`).
Note that most existing history predates this rule, so match the rule and not the log.

Bug reports need reproduction steps; an unreproducible bug cannot be regression-tested.

For work planned through Spec Kit, the `.specify/` workflow produces artifacts under `specs/`,
and `plan-template.md`'s Constitution Check is evaluated against the principles before Phase 0
research and again after Phase 1 design.

## Agent layout

Author agent-facing content once under `.agents/` — `skills/`, `commands/`, `rules/`. The
`.claude/` directory is an adapter: its `skills/`, `commands/`, and `rules/` are symlink views of
the matching `.agents/` directory, so never edit them there or add a second copy of a skill under
an adapter. Only genuinely Claude-specific files (settings, hooks, subagents) are real in
`.claude/`.

## Definition of done

1. `make tests` passes (all five gates).
2. Tests cover the change; a fix has a test that failed before it.
3. Docs updated under `docs/` if behaviour changed, with notebooks re-executed if touched.
4. `CHANGELOG.rst` has an entry for anything user-visible, with its issue or PR number.
5. Generated API `.rst` files committed if modules were added or removed.
6. Any deliberate deviation from the constitution is stated in the pull request.
