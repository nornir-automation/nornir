# Validation: Runner Streaming, Cancellation, and Timeouts

**Feature**: 003-runner-streaming-cancellation | [Tasks](tasks.md)

Evidence for the gate tasks. Each entry gives the command and its result.

## T001: Baseline (2026-10-19, commit 8132783)

| Command | Result |
|---|---|
| `uv sync --locked` | Resolved 171 packages, checked 164; no change |
| `make pytest` | 330 passed; total coverage 93% |
| `make mypy` | Success: no issues found in 62 source files |

No existing failure.

## T014: Phase 2 gate (2026-10-19)

| Command | Result |
|---|---|
| `make pytest` | 358 passed (330 existing, unchanged, plus 28 new) |
| `make mypy` | Success: no issues found in 67 source files |
| `make ruff` | All checks passed |

Notes:

- T003 to T005 were written before the implementation. One test in T004 was wrong:
  it cancelled before `task.run(sub)`, but the start of a subtask is itself a checkpoint
  (R4), so the subtask never starts. The test now cancels from inside the running
  subtask.
- The rename of `_is_coroutine_task` to `_is_async_task` (T033) and the generator
  drivers (T034) were written in this phase, because `Task._start_steps` and
  `Task.astart` were restructured here. Their tests are still the US3 tests.
- `Nornir.submit`, `run_stream`, `asubmit`, `astream` and the handle and stream classes
  (T019–T022) were written in this phase too, so that `nornir/core/run.py` and
  `nornir/core/__init__.py` were each edited once. They are tested in Phase 3.
- `ruff format --check .` reports two files outside this change
  (`tests/plugins/connections/test_async_echo.py`, `tests/plugins/runners/test_asyncio.py`);
  they are untouched, and `make ruff` runs `ruff check` only.

## T024: Phase 3 gate, US1 (2026-10-19)

| Command | Result |
|---|---|
| `make pytest` | 406 passed |
| `make mypy` | Success: no issues found in 70 source files |
| `make ruff` | All checks passed |

Notes:

- The handle, stream and entry-point code was written in Phase 2 (see T014), so most US1
  tests passed on their first run. Two failed first:
  - Zero hosts on `asubmit`: the handle was not finished on return. It is now finalized
    synchronously, as `submit` does.
  - `test_same_code_on_serial_and_threaded_runners`: the test wrongly expected `h002` to
    be never started on `ThreadedRunner(num_workers=1)`. A threaded worker picks up the
    next host as soon as the previous one ends, before the consumer's loop body runs.
    Both runners record the same error types (FR-001); only `started` on that one host
    can differ. The test now checks `started=False` from `h003` on the threaded runner.
- SC-001 measured on 100 hosts with one checkpoint per second: the run finished within
  2 s of `cancel()` on `ThreadedRunner` and on `AsyncioRunner`.

## T030: Phase 4 gate, US2 (2026-10-19)

| Command | Result |
|---|---|
| `make pytest` | 425 passed |
| `make mypy` | Success: no issues found in 72 source files |
| `make ruff` | All checks passed |

Notes:

- The deadline code (T027–T029) was written in Phase 2 with the run context, so the
  US2 tests passed on their first run.
- SC-003: `ThreadedRunner(timeout=2)` with two blocked hosts returned within 3 s.
- SC-002: `AsyncioRunner(per_host_timeout=0.5)` with hosts awaiting forever returned
  within 0.6 s.
- The configuration test goes through `load_runner`, the function `InitNornir` uses to
  pass `runner.options` to the runner constructor.

## T036: Phase 5 gate, US3 (2026-10-19)

| Command | Result |
|---|---|
| `make pytest` | 445 passed; total coverage 93%; `nornir/core/run.py` 95%, `nornir/core/task.py` 90%, `nornir/plugins/runners/__init__.py` 97% |
| `make mypy` | Success: no issues found in 74 source files |
| `make ruff` | All checks passed |

Notes:

- `Nornir.arun` and `Task.arun` now annotate `task` as
  `Callable[..., Coroutine[Any, Any, Any] | AsyncGenerator[Any, None]]`. The parameter
  type is wider; no existing caller is affected.
- `pyproject.toml` gains one per-file ignore, with a comment: `B901` for
  `tests/core/test_run_progress.py`, because progress-reporting tasks are generators that
  `return` their final result by design.
- An async generator cannot `return` a value in Python. An async progress task therefore
  ends by yielding its final `Result` (`Task._adrive`). The `async def` example in
  #1086, which uses `return Result(...)` inside an async generator, is a `SyntaxError`.
  A `def` generator may also yield a `Result` to end, for symmetry.

## T037–T040: Documentation (2026-10-19)

- `docs/howto/long_running_tasks.ipynb` (with `docs/howto/long_running_tasks/`: config and
  a four-host inventory) covers progress with `run_stream` and a progress processor,
  abort on first failure with `submit`, `results()` and `cancel()`, and deadlines on the
  runner and per run. Executed with `jupyter nbconvert --execute --inplace`; nothing was
  edited by hand. `nbval` passed three runs in a row on the new notebook. The examples
  use one worker and print error type names only, so no output varies between runs and
  `docs/nbval_sanitize.cfg` needed no change.
- `docs/tutorial/failed_tasks.ipynb` and `docs/tutorial/task_results.ipynb` were
  re-executed. Their stored tracebacks named the frame `task.py, line 172, in start`;
  a plain task is now called from `Task._start_steps`, so the frame reads
  `line 243, in _start_steps`. The frame below it is still the user's task. The diff of
  those notebooks otherwise holds only execution timestamps, kernel temp paths and the
  kernel's Python version.
- `docs/plugins/execution_model.rst` gains a section on streaming, cancellation and
  deadlines: the runner table, the four `SerialRunner` differences (FR-003), the
  processor-thread table (FR-029), the limits on threads, and a part for runner authors.
- `CHANGELOG.rst`: two entries under 3.7.0, both for #1086 (the feature, and the
  generator-task fix).
- `make docs` generated `docs/api/nornir/core/run.rst`; no other file under `docs/api/`
  changed. The build reports 52 warnings, none from a file this change adds or edits.

## T041: Quickstart scenarios (2026-10-19)

| Scenario | Covered by | Result |
|---|---|---|
| 1. Abort on first failure (SC-001, SC-004) | `test_run_handle.py`, `test_async_run_handle.py` | pass; 100 hosts done within 2 s of `cancel()` on both runners |
| 2. Same code on serial and threaded (FR-001) | `test_run_stream.py::test_same_code_on_serial_and_threaded_runners`, `::test_submit_on_serial_runner_names_run_stream` | pass |
| 3. Run deadline, blocked host (SC-003) | `test_run_deadlines.py::test_run_deadline_returns_on_time_with_a_blocked_host` | pass; returned within 3 s with `timeout=2` |
| 4. Immediate cancellation on asyncio (SC-002) | `test_async_run_deadlines.py`, `test_async_run_handle.py::test_cancel_interrupts_an_await_without_checkpoint`, `::test_cancelling_the_arun_coroutine_still_records_nothing` | pass |
| 5. `except Exception` (FR-017, FR-018) | `test_run_context.py`, `test_run_errors.py` | pass |
| 6. Progress (US3) | `test_run_progress.py`, `test_async_run_progress.py`, notebook | pass |
| 7. Early exit cancels (FR-009) | `test_run_stream.py` | pass |
| 8. Existing behaviour (SC-005) | the 330 existing tests, `make nbval`, `test_run_contract.py` legacy runner and processor | pass |
| 9. CI matrix (SC-006) | | pending CI. Locally: Python 3.10, 3.12 and 3.14 on Linux, 445 passed on each |

## T042: Full gate (2026-10-19)

`make tests`, exit status 0:

| Gate | Result |
|---|---|
| `ruff check .` | All checks passed |
| `mypy nornir tests` | Success: no issues found in 74 source files |
| `nbval` | 135 passed |
| `pytest` | 445 passed; total coverage 93% |
| `docs` | build succeeded, 52 warnings (none from this change) |

Separately, with `UV_PROJECT_ENVIRONMENT` set to a scratch directory:
`uv run --locked --python 3.10 pytest tests` and the same with `--python 3.12` gave
445 passed each. Windows and macOS were not run locally.

## T043: Design documents updated (2026-10-19)

Changes made during implementation, now in the contracts, data model and research:

- `RunContext` gained `running_hosts()`, `completed()`, `aggregated()` and
  `add_change_callback()`. `wait_for_change()` was dropped: the in-tree coordinators
  use their own condition, so that the run's lock is never held while a coordinator
  waits.
- `RunnerCapabilityError` takes a `background` flag for the `SerialRunner` message.
- A yielded `Result` ends a progress task; required for async generators.
- Runners expose their default deadlines as `run_options`.
- `Nornir.arun` and `Task.arun` widen the `task` annotation to accept async generators.
