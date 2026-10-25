# Quickstart: Validating Operations

**Feature**: 004-typed-operations | [Plan](plan.md)

This guide lists the scenarios that prove the feature works end to end, and the commands
that run them. Interfaces are in [contracts/api.py](contracts/api.py),
[contracts/errors.md](contracts/errors.md) and
[contracts/entry-points.md](contracts/entry-points.md).

## Prerequisites

- Spec 003 merged on the branch.
- `uv sync --locked`.

## Commands

| Step | Command | Expected |
|---|---|---|
| Unit and integration tests | `make pytest` | All tests pass, including `tests/core/test_operations*.py`. |
| Type checks | `make mypy` | Pass, including the typing fixtures below. |
| Notebook | `make nbval` | `docs/howto/operations.ipynb` re-executes with its stored output. |
| Full gate | `make tests` | All five gates pass. |

## Scenarios

| # | Scenario | Covers | How it is checked |
|---|---|---|---|
| 1 | An inventory with `ios`, `eos` and `junos` hosts; `get_config` registered for each with `napalm`. `run_operation(GetConfig, connection="napalm", params=GetConfigInput())` yields one typed result per host, each from its own platform's task. Repeat on `SerialRunner` and `ThreadedRunner`. | US1-1, FR-001, FR-004, SC-001 | pytest, parametrised over the two runners |
| 2 | Same as 1 without `connection=`, with `core.operation_connection: napalm` in the config. Then with neither set: `OperationConnectionNotSetError` before any task runs. | US1-2, FR-005 | pytest |
| 3 | `submit_operation(...)` on `ThreadedRunner` returns a handle; `handle.results()` gives the same results. On `SerialRunner`, `RunnerCapabilityError`. | US1-6, FR-002 | pytest |
| 4 | `arun_operation` and `asubmit_operation` on `AsyncioRunner` with `async def` implementations. | FR-003 | pytest (asyncio) |
| 5 | A typing fixture module type-checked by mypy with the repository settings: `res.result.config` is `str` (checked with `assert_type`), a `lambda` returning the wrong type is rejected, `run_operation("get_config", ...)` gives `RunStream[Any]`, and annotations with bare `Result`, `RunStream`, `RunHandle` pass. | FR-006, FR-008, FR-021, SC-002 | `make mypy` on the fixture; the expected-error case through a pytest that runs mypy on a snippet |
| 6 | A host with platform `panos` and a host with no platform: each fails with `OperationNotRegisteredError` and its own message; the other hosts succeed. | US1-3, FR-012, FR-013 | pytest |
| 7 | An implementation that returns a `dict`: `OperationOutputError` for that host. | US1-4, FR-011 | pytest |
| 8 | `params={"sanitize": True}`: `OperationInputError` with "did you mean 'sanitized'?", raised by `run_operation` itself; no task runs. Repeat with a Pydantic input model if Pydantic is available in the development environment, otherwise with a stub class that has `model_validate`. | US1-5, FR-007, FR-009 | pytest |
| 9 | An implementation that returns `Result(result=Out(...), changed=True, diff="d")`, and one that returns `Result(failed=True, exception=err)`. | US2, FR-010, FR-011 | pytest |
| 10 | `params=lambda host: In(path=host.name)`; then a callable that raises for one host only. | US3, FR-008 | pytest |
| 11 | A run that mixes a `def` and an `async def` implementation, on `ThreadedRunner` and on `AsyncioRunner`. | FR-014 | pytest |
| 12 | Registry: same task twice (accepted), different task (error naming both sources), `replace=True`, `platform=None` (`ValueError`), two Operation classes with one name (error), the same class definition executed twice (replaced). | US4-3, US4-4, FR-016, FR-018 | pytest |
| 13 | Entry points: a test distribution on `sys.path` with a `.dist-info/entry_points.txt` that declares one contract, two implementations, a malformed name, and a conflict. Check `operations()`, the sources, and the two errors. | US4-1, US4-2, FR-015, FR-015a, FR-017, FR-019, FR-020 | pytest with a temporary `sys.path` entry |
| 14 | A traceback from an implementation that raises shows the same number of Nornir frames as the same function run with `nr.run`. | FR-022 | pytest comparing `traceback.extract_tb` lengths |
| 15 | `PartialResult`, `task.checkpoint()`, `per_host_timeout` and `cancel()` inside an implementation behave as for a plain task. | FR-024 | pytest, reusing spec 003 helpers |
| 16 | The existing suite passes unchanged, and `pyproject.toml` has no new runtime dependency. | FR-023, SC-004 | `make pytest`, review of the diff |
| 17 | Before release: a package outside this repository (a `nornir_napalm` prototype branch or NornFlow) registers implementations through entry points and runs against the release candidate. | SC-005 | Manual, recorded in the pull request |

## Documentation deliverables

- `docs/howto/operations.ipynb`: define an Operation, implement it for two platforms, run it,
  read typed results, show one failure. Executed in CI (SC-001).
- `docs/howto/index.rst`: link the notebook.
- `docs/configuration/parameters.rst`: the `operation_connection` entry.
- `docs/api/nornir/core/operations.rst`: regenerated by `make docs` and committed.
- `CHANGELOG.rst`: an entry that references #1089.
