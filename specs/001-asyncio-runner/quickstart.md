# Quickstart: validating the Asyncio Runner end to end

**Feature**: 001-asyncio-runner | **Plan**: [plan.md](plan.md) | **Contracts**: [contracts/](contracts/)

This is a validation guide: the scenarios below prove the feature works once implemented.
Implementation detail lives in `tasks.md` and the code.

## Prerequisites

```bash
uv sync --locked          # the only supported environment manager
uv run python --version   # any of 3.10 – 3.14
```

## 1. The authoritative gate

```bash
make tests                # ruff, mypy, nbval, pytest, docs — all five must pass
```

Expected: green on Linux, macOS and Windows for every supported Python. The pre-existing suite
passes with exactly one modified assertion (`test_registered_runners` now includes `asyncio`).

## 2. Focused loops while implementing

```bash
make pytest ARGS="tests/plugins/runners tests/core/test_async_run.py tests/core/test_async_tasks.py tests/core/test_async_connections.py tests/plugins/connections"
make mypy
make ruff && uv run ruff format --check .
make nbval                # re-executes docs/howto/asyncio_runner.ipynb among the others
make docs                 # Sphinx must build the new prose page and literalinclude the fixture
```

## 3. Scenario checks (each maps to a spec story or criterion)

### US1 — run async tasks from inside an event loop

```python
import asyncio
from nornir import InitNornir

async def hello(task):
    await asyncio.sleep(0.01)
    return f"{task.host.name} is up"

async def main():
    nr = InitNornir(config_file="docs/howto/asyncio_runner/config.yaml")   # runner: asyncio
    result = await nr.arun(hello)
    assert set(result) == set(nr.inventory.hosts)
    assert not result.failed

asyncio.run(main())
```

Expected: one `MultiResult` per host; processor events in the same order as a threaded run
(covered by `tests/core/test_async_run.py`).

### US1 scenario 3/4 — subtask failure and `failed_hosts`

Covered by `tests/core/test_async_tasks.py` (`task.arun` of a raising subtask records a failed
`Result`, the parent receives `NornirSubTaskError`, the host lands in `nr.data.failed_hosts`
and is skipped by the next `arun` with default `on_good`/`on_failed`).

### US1 scenarios 5–8 and the seven-surface error matrix

Run `tests/core/test_async_run.py -k error` and `tests/core/test_async_tasks.py -k error`.
Expected: every case in [contracts/errors.md](contracts/errors.md) raises the named class and no
`task_instance_started` was observed by the recording processor.

### US2 — async connection plugin through `AsyncEcho`

```bash
make pytest ARGS="tests/plugins/connections/test_async_echo.py -vs"
```

Expected: the echo server starts on an ephemeral port on `127.0.0.1`, each host's task obtains
the connection with `await task.host.aget_connection("async_echo", task.nornir.config)`, sends a
payload, receives it back, a second `aget_connection` does not reopen, and `aclose_connections`
empties every host's connection table. Must pass on Windows too (Proactor loop).

### US2 scenarios 2–4 — sync/async plugin combinations and the shared cache

Covered by `tests/core/test_async_connections.py` using three dummies (sync-only, async-only,
both): `aget_connection` on sync-only raises `ConnectionPluginNotAsyncError`; `get_connection`
on async-only raises `ConnectionPluginNotSyncError`; a connection opened by the sync path is
returned by `aget_connection` without `aopen` being called; two concurrent `aget_connection`
calls for the same name make the second raise `ConnectionAlreadyOpen`.

### US3 — cleanup with `async with`

```python
async with InitNornir(config_file="docs/howto/asyncio_runner/config.yaml") as nr:
    await nr.arun(hello)
# every host's `connections` is empty here, failed hosts included
```

Covered by `tests/core/test_async_run.py` (mixed sync + async connections on one host, a second
host marked failed, a recording processor sees `task_started` for the cleanup task).

### US4 — cancellation

Covered by `tests/plugins/runners/test_asyncio.py::test_cancel_propagates`: cancel the awaiting
`arun` after the first host started; expect `asyncio.CancelledError` at the caller,
`asyncio.all_tasks()` free of host coroutines, `failed_hosts` unchanged, no `task_completed`.

### SC-002 / SC-003 — performance

```bash
make pytest ARGS="tests/plugins/runners/test_asyncio.py -k 'starve or thousand'"
```

Expected: 1,000 hosts × 100 ms with `num_workers=1000` in < 2 s and unchanged
`threading.active_count()`; a heartbeat coroutine beside a 100-host run never gaps > 50 ms.

### SC-005 — two methods make a plugin async-capable

Take `DummyConnectionPlugin` from `tests/core/test_connections.py`, add `aopen`/`aclose` (the
"both" dummy in `tests/core/test_async_connections.py` is exactly that), register it once, and
use it from both `get_connection` and `aget_connection`. No registration or configuration change.

### SC-006 — documentation

```bash
make nbval && make docs
```

Expected: `docs/howto/asyncio_runner.ipynb` re-executes with matching stored output (errors are
printed from `except` blocks, so they are stable), and the built HTML contains the
`writing_async_connection_plugins` page with the `AsyncEcho` source inlined.

## 4. Before opening the pull request

- [ ] `CHANGELOG.rst` has a `3.7.0` entry naming #1085 and the sync-path behaviour change.
- [ ] The follow-up issue for synchronous tasks in async runs exists and its URL replaced
      `#1085` in `SYNC_TASKS_IN_ASYNC_RUNS_ISSUE`.
- [ ] The PR description restates maintainer approval for `AsyncioRunner` as an in-tree plugin
      (Constitution II) and lists the two spec deviations from [plan.md](plan.md).
- [ ] `docs/api/nornir/**` unchanged (`git status` clean after `make docs`).
