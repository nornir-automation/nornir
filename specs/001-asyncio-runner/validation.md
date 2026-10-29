# Validation: Asyncio Runner

## Baseline

- Platform: Linux 7.0.0-1012-aws x86_64, glibc 2.43
- Interpreter: CPython 3.13.14
- `uv sync --locked`: passed (171 packages resolved, 164 checked)
- `make pytest`: passed (130 tests, 6.10 seconds, 90% coverage)
- `make mypy`: passed (48 source files)

## Foundation Checkpoint

- `make pytest`: passed (130 tests in 6.01 seconds)
- `make mypy`: passed (48 source files)
- `make ruff`: passed

## US1 Async Dispatch Checkpoint

- Failing-first evidence: runner collection failed before `AsyncioRunner`; Task tests had 8 expected failures; Nornir tests had 25 expected failures.
- Focused `make pytest`: passed (64 tests in 0.67 seconds).
- Performance: 100-host heartbeat and 1,000-host/thread-count tests passed at specified thresholds.
- `make mypy`: passed (51 source files).
- `make ruff`: passed.
- Debuggability: `Task.astart` directly awaits the original user callable; traceback tests confirm user source/name visibility.

## US2 Capability Connections Checkpoint

- Test-first registry stream: 17 expected Host-dependent failures remained.
- Host stream red: 38 failed, 25 passed.
- AsyncEcho: observed missing behavior before implementation.
- `make pytest ARGS="tests/core/test_capability_plugins.py tests/core/test_async_connections.py tests/plugins/connections tests/core/test_connections.py tests/core/test_pickle.py"`: passed (67 tests in 0.46 seconds).
- `make mypy`: passed (55 source files).
- `make ruff`: passed.

## US3 Async Cleanup Checkpoint

- Failing-first evidence: 9 failed, 33 passed before the Nornir-level async cleanup and context implementation.
- `make pytest ARGS="tests/core/test_async_run.py tests/core/test_async_connections.py tests/plugins/connections"`: passed (70 tests).
- `make mypy`: passed.
- `make ruff`: passed.

## US4 Cancellation Checkpoint

- Expanded cancellation evidence passed for active and queued runner work, repeated caller cancellation while draining, aggregate exception retrieval, cancelled connection open/close with retry-safe state, and AsyncEcho partial-transport and handler cleanup.
- No implementation correction was required after the expanded tests.
- `make pytest ARGS="tests/plugins/runners tests/core/test_async_connections.py tests/plugins/connections"`: passed (53 tests).
- `make mypy`: passed.
- `make ruff`: passed.

## Documentation Checkpoint

- Initial `make nbval` identified legitimate traceback-line drift in stored notebook output.
- Re-executed `docs/tutorial/failed_tasks.ipynb` and `docs/tutorial/task_results.ipynb` rather than editing their output by hand.
- Final `make nbval`: passed (123 tests).
- `make docs`: succeeded with 44 pre-existing/generated-documentation style warnings.

## Distribution Checkpoint

- `make wheel`: built the source distribution and wheel.
- The isolated wheel importability check passed using Python 3.14.6.
- Wheel inspection confirmed that it contains `nornir` and the `asyncio` runner entry point, and excludes `tests/` and `AsyncEcho`.
- Rebuilt the wheel after the final contract-validation fix; isolated import passed again under Python 3.14.6.

## Independent Review

- Independent review found that operation descriptors could be inaccessible.
- The finding was fixed with a failing regression test added before the correction.
- Final focused verification passed: 25 tests, mypy, and Ruff.

## Authoritative Gate

- The initial full `make tests` run exposed an order-dependent zero-host warning test; the test was corrected and the entire gate was rerun successfully.
- Ruff passed.
- mypy passed (55 source files).
- nbval passed (123 cells).
- pytest passed (258 tests in 6.63 seconds, 92% coverage).
- Documentation succeeded with 44 warnings.

## Pending Release Gates

- T056 is done (2026-10-29): the follow-up issue is
  https://github.com/nornir-automation/nornir/issues/1120.
- T061 remains pending.

## Python 3.14 CI Follow-up

- Push CI for commit `e4b797a` failed because Python 3.14 reports a cancelled
  `asyncio.shield` wrapper as `CancelledError exception in shielded future`.
- Reproduced with Python 3.14.6 using the existing aggregate-exception cancellation test.
- Replaced the initial shield wrapper with `asyncio.wait`, which preserves cancellation
  isolation without installing Python 3.14's exception-logging shield callback.
- Python 3.14: 25 runner tests, 258 full tests, mypy, Ruff, and 123 nbval tests passed.
- Python 3.10: 25 runner tests passed.
- Push CI for fix commit `777cd55` passed on Python 3.10-3.14 across Ubuntu, macOS,
  and Windows, including linters, Sphinx, and wheel import:
  https://github.com/nornir-automation/nornir/actions/runs/36307946893

## Phase 8: Mode binding for dual-capability plugins (2026-10-13)

- Trigger: nornir_scrapli commit 6dd01bf showed that a dual plugin cannot serve one
  transport from both modes and that the Host returned opposite-mode cache hits.
- Spec revision committed as `a132c4c` (FR-012/014 amended, FR-024 added, research R15).
- T062: `tests/core/test_async_connections.py` now asserts the mode mismatch in both
  directions, intact cache on rejection, synchronous close of an asyncio-bound connection
  rejected, asynchronous close of a sync-bound connection calling `close`, reopening in the
  other mode after close, `Host.connection_mode` for every plugin kind, and bulk cleanup by
  bound mode. The Nornir-level mixed cleanup test was corrected for sync-bound dual plugins.
- T063: `ConnectionModeMismatchError(connection_name, opened_in, requested)` added under
  `SyncAsyncMismatchError`; the message names the bound mode and the matching close method.
- T064: `_CapabilityConnectionState.mode` recorded on publish; `Host.connection_mode`
  added; mode enforced on cached get in both directions and on synchronous close;
  asynchronous close selects `close` or `aclose` by bound mode instead of by capability.
- T065: dual facet docstring, the plugin-author guide (facet bullet and the host caching
  section, now "mode binding"), and the changelog entry updated. `docs/plugins/*` had no
  reuse wording to change.
- T066 evidence, all run locally on this branch:
  - Focused pytest (connection, capability, run, AsyncEcho, legacy connection tests):
    114 passed.
  - Full `make pytest`: 260 passed (258 before this phase; two tests added).
  - `make mypy`: no issues in 55 source files.
  - `make ruff`: all checks passed; edited files formatted with `ruff format`.
  - `make docs`: build succeeded with 44 warnings, the same count as before; no change
    to the generated API reference.
  - `make nbval`: 123 passed; the asyncio notebook output did not change, so it was not
    re-executed.
- speckit-analyze re-run (2026-10-13): 24 functional requirements and 7 success
  criteria, 66 tasks, 100% requirement coverage, no placeholders, no duplicates, no
  constitution conflicts. Findings were all LOW or MEDIUM: completed Phase 4 and Phase 7
  task texts (T026, T036, T037, T053) still carry the superseded cross-mode reuse
  wording, Phase 8 is absent from the plan's sequencing list and the tasks phase graph,
  and `Host.connection_mode` returns the asyncio entry when a name sits in both caches
  instead of raising the contract error the other lookups raise. T056 and T061 remain the
  open merge preconditions.

## Phase 9: Convergence (2026-10-28)

- speckit-converge run against the rebased branch found two remaining items and
  appended them as T067 and T068; T056 and T061 stay open as merge preconditions.
- T067: `Host.connection_mode` now runs the same cache-conflict check as the other
  lookups, so a name present in both the public and the private cache raises
  `ConnectionPluginContractError` instead of reporting `"asyncio"`. The existing
  conflicting-entries test in `tests/core/test_async_connections.py` asserts it; the
  assertion failed before the change (`DID NOT RAISE`) and passes after it.
- T068, CI matrix evidence for the current head. The constitution now lists Python 3.10
  through 3.15; the runs below postdate the Phase 8 mode-binding commits and the two
  rebases onto `main` (2026-10-24 and 2026-10-27):
  - Run 38511079705 on commit `01bac1d` (mode binding, before the rebases): success,
    17 jobs, Python 3.10-3.14 on Ubuntu, macOS and Windows.
  - Run 40114897109 on commit `9586c5e` (first rebase): success, 17 jobs.
  - Run 40483242882 on commit `51c322f` (second rebase, main with Python 3.15 support):
    success, 20 jobs: linters, build and import wheel, and Python 3.10, 3.11, 3.12,
    3.13, 3.14 and 3.15 on ubuntu-latest, macos-15 and windows-2022.
    https://github.com/nornir-automation/nornir/actions/runs/40483242882
- Local gates after T067 on this branch: `make ruff` clean and both edited files already
  formatted; `make mypy` no issues in 56 source files; `make pytest` 262 passed;
  `make docs` build succeeded with 45 warnings, all of them the pre-existing notebook
  cross-reference and duplicate-object warnings; none names the edited docstring, and
  the generated API reference under `docs/api/nornir/` did not change. The Phase 8
  count of 44 was measured before the two rebases onto `main`.

## Phase 10: Review revision (2026-10-28)

- Trigger: review of PR #1111 and the five failing tests in #1119.
- T069: the five #1119 tests were taken over with credit. The processor-failure test
  and the in-task `CancelledError` test are unchanged apart from a `failed` event on
  the processor fixture; the in-task test runs on every version (no 3.10 skip) because
  the runner makes the distinction per host there. The two error-drain tests were
  rewritten as `test_caller_cancellation_after_a_host_error_is_not_lost` and
  `test_timeout_after_a_host_error_raises_timeout_error`: the caller cancels or times
  out while the runner waits for the other host after a host error, since a host error
  no longer starts the drain. `test_astart_does_not_convert_base_exception_to_result`
  was replaced by `test_astart_records_cancelled_error_raised_by_the_task` (3.11+),
  `test_astart_re_raises_cancelled_error_on_python_310` (3.10 only) and
  `test_astart_propagates_cancellation_of_its_asyncio_task`.
- T070: pending-open tests rewritten and added: an asynchronous get waits and shares
  the transport while explicit open and synchronous get raise; three concurrent gets
  share one `aopen`; a failed open raises in the waiter; a cancelled opener releases
  the waiter, which opens the connection itself. Before the implementation the four
  new tests failed with ConnectionAlreadyOpen or a hang in the waiter.
- T071: the synchronous bulk cleanup test now asserts attempt-all, and a new test
  opens a dual connection in asyncio mode before a legacy and a sync one and asserts
  both synchronous closes happen before ConnectionModeMismatchError is raised.
- T072: a parametrized test asserts the five connection errors are ConnectionException
  instances carrying `connection`, and the capability-registry tests assert it for the
  ambiguity and contract errors.
- T073: `AsyncioRunner.arun` gathers with exceptions returned, waits for every host,
  then raises the first host error in host order through `_collect`; only a caller
  cancellation runs `_cancel_and_drain`. `Task.astart` records a `CancelledError`
  when `asyncio.Task.cancelling()` reports no pending cancellation (3.11+) and
  re-raises otherwise; `Task._record_unrequested_cancellation` lets the runner record
  a `CancelledError` from a host it did not cancel on every version.
- T074: `_opening` is now `dict[str, asyncio.Future[None]]`; `aget_connection` awaits
  a pending future before the cache-hit checks; `aopen_connection` sets the failure on
  the future (and marks it retrieved) or resolves it in `finally`, so a cancelled open
  releases the waiters without a cancellation of their own. Publication moved to
  `_publish_async_opened` to keep the try clause short.
- T075: `Host.close_connections` attempts every name and raises the first error after
  the last attempt; the five connection errors add ConnectionException as a base with
  `connection` set to the name, keeping SyncAsyncMismatchError first for the three
  mode errors. `ConnectionException` moved above them in `exceptions.py`.
- T076: `docs/plugins/execution_model.rst` gained a paragraph on errors and
  cancellation; the plugin-author guide covers waiting on an opening name, the inline
  `close` blocking the loop during asynchronous cleanup, and attempt-all bulk cleanup;
  `CHANGELOG.rst` records the runner error semantics, shared opens, error bases, and
  the `Host.close_connections` behaviour change.
- T077: `docs/tutorial/failed_tasks.ipynb` and `task_results.ipynb` were re-executed
  inside the CI Docker image (Python 3.13 build of the repository `Dockerfile`, with
  the current `nornir` package mounted so line numbers match the final code). Stored
  tracebacks now show `/nornir/nornir/core/task.py`; no `/home/` path remains in any
  notebook. `docs/nbval_sanitize.cfg` gained `regex5` for home-directory paths.
  `docs/howto/asyncio_runner.ipynb` output did not change, so it was not re-executed.
- Gates, all run locally on this branch after the changes:
  - `make ruff`: all checks passed. `ruff format --check` reports only the
    pre-existing `make_nornir` signature in `tests/plugins/runners/test_asyncio.py`.
  - `make mypy`: no issues in 56 source files.
  - `make pytest`: 276 passed, 1 skipped (the 3.10-only astart test).
  - Python 3.10 (`uv run --python 3.10`): 74 passed, 1 skipped across the runner,
    task and connection tests; the in-task cancellation test passes through the
    runner's per-host fallback.
  - `make nbval`: 123 passed.
  - `make docs`: build succeeded with the same 45 pre-existing warnings; no change to
    the generated API reference.
- CI on head 2394bd0 (commits b917350 and 2394bd0 pushed on 2026-10-28): the two
  `test nornir` runs, 40762125612 (push) and 40762133502 (pull request), succeeded with
  all 20 jobs each: the linters job, the wheel build and import job, and the test
  matrix of Python 3.10 through 3.15 on ubuntu-latest, macos-15 and windows-2022.
- speckit-analyze on the revised artifacts: no CRITICAL, HIGH or MEDIUM finding; five
  LOW items (a stale "six mismatches" comment in the plan targets, R6 still naming the
  set-based reservation, superseded wording in completed historical tasks, the spec
  status still "Draft", and FR-026 not pointing at the Python 3.10 assumption). All 27
  functional requirements and 7 success criteria have a task; no task is unmapped.
- T078 remaining: the replies on the PR #1111 review threads, which wait for the
  author's approval of the drafted text.

## T056: follow-up issue (2026-10-29)

- Opened https://github.com/nornir-automation/nornir/issues/1120 for synchronous tasks
  in async runs, threads during asynchronous cleanup, and the opt-in surface.
- `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE` now points to #1120. `tests/core/test_async_run.py`
  reads the constant, so no test expectation changed.
- `docs/howto/asyncio_runner.ipynb` was re-executed; the only output change is the
  issue URL in the `SyncTaskOnAsyncRunError` message.
