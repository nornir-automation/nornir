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

- T056 is blocked because the user declined creation of the synchronous-tasks-in-async-runs follow-up issue.
- T060 is unavailable because no remote pull request or CI matrix exists.
- T061 remains pending on both T056 and T060.

## Python 3.14 CI Follow-up

- Push CI for commit `e4b797a` failed because Python 3.14 reports a cancelled
  `asyncio.shield` wrapper as `CancelledError exception in shielded future`.
- Reproduced with Python 3.14.6 using the existing aggregate-exception cancellation test.
- Replaced the initial shield wrapper with `asyncio.wait`, which preserves cancellation
  isolation without installing Python 3.14's exception-logging shield callback.
- Python 3.14: 25 runner tests, 258 full tests, mypy, Ruff, and 123 nbval tests passed.
- Python 3.10: 25 runner tests passed.
