# Tasks: Workflow smoke test

## Phase 1: Smoke

**Purpose**: Prove that the phased loop can implement, validate and report one trivial group.

- [X] T001 Create `docs/_workflow_smoke.txt` containing exactly the line `implement-phased smoke test` (with a trailing newline); nothing else changes
- [X] T002 Run `make ruff` and `make mypy` and confirm both are green (no file edits)

**Checkpoint**: The smoke file exists with the exact content and the gates are green.
