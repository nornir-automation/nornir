<!--
Sync Impact Report — v1.1.0
=====================================
Version change: 1.0.0 → 1.1.0

Amendment incorporating maintainer review on PR #1094 (ogenstad):

- Principle IV: inherently platform-specific functionality is directed out of tree as a plugin
  (aligning with Principle II) rather than merely being declared in the pull request.
- Quality Gates / Dependency policy: development dependencies MAY be pinned or range-constrained
  in pyproject.toml — nothing downstream is affected and the constraint doubles as a quick
  reference — while runtime dependencies stay as loose as possible for broad installation.
  Prose documents no longer cite dependency versions; pyproject.toml and uv.lock are the
  reference. This resolves the former TODO(DEV_DEPENDENCY_PINS) in favour of the pins, and
  drops the ruff-only exact-pin special case.

Propagation status:
  ✅ CONTRIBUTING.rst — "Updating dependencies" pinning guidelines rewritten to match.
  ✅ AGENTS.md — the "known drift" caveat replaced by the ratified policy, version numbers removed.
  ✅ .specify/templates/ — no constitution-specific text to keep in sync; no edit needed.

Deferred TODOs:
  - TODO(COMMIT_CONVENTION): Conventional Commits is stated as a forward requirement. Recent
    history does not follow it (16 of the last 60 subjects carry a type prefix), so the rule
    binds new work rather than describing existing history.
-->

# Nornir Constitution

## Core Principles

### I. Python-First, No DSL (NON-NEGOTIABLE)

Nornir is a library driven from Python, not a runtime configured by a bespoke language.
Features MUST be expressed as Python objects, functions, and types that users call directly.

The project MUST NOT introduce a domain-specific language, a template-driven execution engine, or
YAML/JSON-defined control flow for describing automation behaviour. Inventory *data* may be
declarative — `SimpleInventory` reads YAML — but automation *logic* may not be.

Every change MUST preserve debuggability with stock Python tooling: a user MUST be able to add
`import pdb; pdb.set_trace()` and step directly into task execution, and tracebacks MUST point at
real user code rather than an interpreter layer.

**Rationale**: This is why Nornir exists. Every DSL-based framework trades this away, and
recovering it later is impossible once control flow lives outside Python.

### II. Thin Core, Capability at the Edge

The core owns three things and no more: inventory modelling, task dispatch and concurrency, and the
plugin registry. Anything that speaks to a specific device, protocol, vendor, or external system
MUST ship as a separate package discovered through the `nornir.plugins.*` entry points.

In-tree plugins are limited to the reference implementations already present: `SimpleInventory`,
`SerialRunner`, and `ThreadedRunner`. Adding another in-tree plugin requires maintainer approval.

The core MUST NOT take a new runtime dependency to serve a single plugin's use case. New runtime
dependencies require explicit maintainer approval and a recorded justification.

**Rationale**: 3.0.0 deliberately unbundled plugins so the ecosystem could move faster than core
and so a broken vendor library could not block a core release.

### III. Typed and Statically Verified

All new and modified code MUST carry complete type annotations and MUST pass `make mypy` under the
repository's configured strictness (`disallow_untyped_defs`, `disallow_any_generics`,
`disallow_untyped_calls`, `warn_return_any`, and the rest of `[tool.mypy]`). `make ruff` MUST pass.

The suppression lists in `pyproject.toml` marked "should be removed once the code has been updated"
are a debt ledger, not a licence. Changes MAY remove entries and MUST NOT add to them without a
comment stating why. A `# type: ignore` or `# noqa` MUST NOT be used where a real fix exists.

**Rationale**: Nornir is a typed library that other packages build against; its annotations are
part of its public surface, and silent erosion of them degrades every downstream plugin.

### IV. Tested Across the Whole Support Matrix

Every behavioural change MUST arrive with tests. A bug fix MUST include a test that fails before
the fix and passes after it.

`make pytest` MUST pass on every supported Python version (3.10 through 3.14) and every supported
platform (Linux, macOS, Windows). Windows is a first-class target, not best-effort: code MUST NOT
assume POSIX path separators, unlimited path lengths, or shell semantics.

Functionality that is inherently platform-specific SHOULD NOT live in the core at all — it belongs
out of tree as a plugin (Principle II). Where a change genuinely cannot be exercised on a platform,
that MUST be stated explicitly in the pull request rather than being silently skipped.

**Rationale**: Nornir runs inside operators' production environments across the full matrix, and
the matrix in CI is the only honest statement of what is actually supported.

### V. Executable, Current Documentation

Documentation is part of the change, not a follow-up. `make docs` (Sphinx) and `make nbval`
(notebook output verification) MUST pass; a change that breaks either is incomplete.

User-visible changes MUST update the relevant page under `docs/` and add a `CHANGELOG.rst` entry.
Tutorial and how-to notebooks MUST contain genuine verified output — never hand-written, edited, or
stale sample output.

**Rationale**: Notebook outputs are executed in CI precisely so documentation cannot drift away
from behaviour. Prose that is not executed is prose that will eventually lie.

### VI. Stable Public API, Semantic Versioning

The public API is everything importable from `nornir` without a leading underscore, plus the plugin
contracts `ConnectionPlugin`, `InventoryPlugin`, `RunnerPlugin`, `Processor`, and
`TransformFunction`.

These contracts are `typing.Protocol` definitions: third-party plugins satisfy them structurally
without subclassing. Changing a signature therefore breaks every conforming plugin at once, with no
inheritance error to catch it. Signature changes MUST be treated as breaking.

Releases follow semantic versioning — MAJOR for breaking changes, MINOR for backward-compatible
additions, PATCH for fixes. A breaking change MUST ship in a MAJOR release accompanied by an
upgrade guide under `docs/upgrading/`. Deprecations MUST emit a warning for at least one MINOR
release before removal.

**Rationale**: An ecosystem of third-party plugins pins against these interfaces, and structural
typing means breakage surfaces at the user's runtime rather than at import.

## Quality Gates and Tooling

`uv` is the only supported dependency and environment manager. Contributors set up with
`uv sync --locked`. `uv.lock` is committed and MUST stay consistent with `pyproject.toml`.

`make tests` is the authoritative gate. It runs `ruff`, `mypy`, `nbval`, `pytest`, and `docs`, and
all five MUST pass before a pull request merges. `make docker-tests` reproduces the CI Linux
environment locally for changes that behave differently outside it.

Dependency policy:

- Runtime dependencies (`[project.dependencies]`) are kept as loose as possible so that Nornir
  installs into the broadest range of environments: pin to the major version when the upstream
  project follows semver, and to an exact version only when it does not. Adding one to the core is
  exceptional and governed by Principle II.
- Development dependencies MAY be pinned or constrained to ranges in `pyproject.toml`: nothing
  downstream is affected, and the constraint doubles as a quick reference for the versions in use.
- `pyproject.toml` and `uv.lock` are the authority on dependency versions. Prose documents MUST NOT
  cite dependency versions — they go stale.
- Adding, removing, or changing a dependency requires **maintainer approval**, recorded in the pull
  request that makes the change. Approval is the gate — a dedicated issue or a separate
  dependency-only pull request is NOT required, and development MUST NOT be blocked waiting for one.
  A feature or fix PR MAY carry the dependency change its own code needs, provided the change is
  limited to what that code actually requires and is called out explicitly for review.
- Dependencies are refreshed deliberately ahead of a release rather than opportunistically. A bulk
  refresh unrelated to any feature SHOULD still land on its own, so that a lockfile churn diff is
  never mixed into a behavioural change.

These pinning rules may be broken for a compelling, stated reason — but the reason MUST be recorded
in the pull request.

## Development Workflow

`main` is the integration branch and the target for pull requests. Work happens on a branch named
for its intent (`feat/`, `fix/`, `docs/`, `chore/`, `refactor/`) or under a contributor-scoped
prefix (`dga/…`); both conventions are in active use. Nobody commits directly to `main` or to a
release branch.

Significant changes to the core MUST have a tracking GitHub issue **before the pull request merges**,
so the design is discussed and recorded in the open. Opening it early is encouraged — the discussion is
most useful before the design sets — but it is **not** a precondition for writing code. Prototyping,
spiking, and exploratory work on a branch MUST NOT be blocked waiting for an issue: the point of a
branch is to be able to build the thing that makes the design arguable in the first place.

Bug reports MUST include reproduction steps; an unreproducible bug cannot be fixed or
regression-tested, and reproduction is the contributor's responsibility to supply.

Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `style:`).
Every pull request MUST pass the full CI matrix and receive maintainer review before merge.

For work planned through Spec Kit, the `.specify/` workflow (specify → plan → tasks → implement)
produces artifacts under `specs/`, and the Constitution Check in `plan-template.md` MUST be
evaluated against the principles above before Phase 0 research and again after Phase 1 design.

## Governance

This constitution supersedes conflicting practice elsewhere in the repository. Where guidance in
`CONTRIBUTING.rst` or `docs/` contradicts it, this document prevails and the other MUST be
corrected.

Amendments require a pull request that states the rationale, updates the version line below, and
propagates the change to dependent artifacts (`.specify/templates/`, `CONTRIBUTING.rst`, and any
affected documentation).

Versioning of this document:

- **MAJOR** — a principle is removed or redefined in a backward-incompatible way.
- **MINOR** — a principle or section is added, or guidance is materially expanded.
- **PATCH** — clarification, wording, or typo fixes that do not change meaning.

Compliance is a review responsibility: reviewers MUST verify that a pull request satisfies the
principles above. Any deliberate deviation MUST be recorded in the pull request with its
justification and, when it affects design, in the Complexity Tracking table of the feature's
`plan.md`.

**Version**: 1.1.0 | **Ratified**: 2026-08-22 | **Last Amended**: 2026-09-06
