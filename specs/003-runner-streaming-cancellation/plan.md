# Implementation Plan: Runner Streaming, Cancellation, and Timeouts

**Branch**: `dga/feat-runner-xoh8k` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Feature directory**: `specs/003-runner-streaming-cancellation`

## Summary

Add an opt-in API for long-running work, as specified from
[#1086](https://github.com/nornir-automation/nornir/issues/1086):

- background runs with a handle (`submit`, `asubmit`);
- live streams (`run_stream`, `astream`);
- cooperative cancellation through `task.checkpoint()`, every `yield`, and every subtask
  start;
- per-host and per-run deadlines, set on the runner or per run;
- progress-reporting generator tasks with `PartialResult` and an optional
  `task_instance_progress` processor hook.

The core gains one public `RunContext` per run. It owns every recording rule that must
be identical on all runners: exactly one result per host, events for hosts that never
started, deadlines, and fan-out to subscribers. Runners implement one of two sibling
protocols, `StreamingRunner.execute` (a generator, so `SerialRunner` can stay on the
caller's thread) or `AsyncStreamingRunner.aexecute`, and only decide when hosts start
and how they are woken. `RunnerPlugin`, `AsyncRunnerPlugin`, `Processor`, `Result`,
`Nornir.run` and `Nornir.arun` keep their signatures.

## Technical Context

- **Language/version:** Python 3.10–3.14. Standard library only: `threading`
  (`Lock`, `Condition`, `Thread`), `concurrent.futures.ThreadPoolExecutor` with
  `shutdown(cancel_futures=True)`, `queue.SimpleQueue`, `asyncio` (`call_at`,
  `Queue`, `shield`), `inspect.isgenerator`/`isasyncgen`, `time.monotonic`, `uuid`,
  `dataclasses`. No `asyncio.timeout` or `TaskGroup` (3.11+).
- **Dependencies:** no new runtime or development dependency.
- **Storage:** none. In-memory state per run (see [data-model.md](data-model.md)).
- **Project type:** pure Python library with structurally typed plugin contracts.
- **Platforms:** Linux, macOS, Windows. No signals and no platform-specific thread
  calls. Timing tests use the margins of SC-001 to SC-003 only.
- **Testing:** `make pytest` during implementation, then `make tests`. Blocking test
  tasks wait on events released at teardown.
- **Performance:** SC-001 (cancellation done within 2 s on 100 hosts with 1 checkpoint/s),
  SC-002 (asyncio interruption within 0.1 s), SC-003 (threaded run returns within
  T + 1 s). No overhead target per partial result (spec Assumptions).
- **Constraints:** existing signatures, protocol members, defaults, entry points and
  result types unchanged. Default runner stays `threaded`.
- **Scope:** `nornir/core/run.py` (new), `nornir/core/task.py`,
  `nornir/core/__init__.py`, `nornir/core/processor.py`, `nornir/core/exceptions.py`,
  `nornir/core/plugins/runners.py`, `nornir/plugins/runners/__init__.py`; tests; one
  executed notebook; execution-model docs; changelog; regenerated API reference.

All unknowns were resolved in [research.md](research.md); none remain open.

## Constitution Check

Design checks assess feasibility, not completed implementation or CI results.

| Principle | Pre-research | Post-design |
|---|---|---|
| I. Python-first, no DSL | PASS: generators, exceptions and plain method calls | PASS: user functions are called directly by the stepping driver, which adds one frame between the core and the user's function, as `start()` does today; `SerialRunner` keeps every task on the caller's thread so `pdb` works (FR-002) |
| II. Thin core | PASS: dispatch and concurrency are core responsibilities; no new dependency | PASS: no new plugin; `RunContext` keeps the recording rules in the core and concurrency in the runners; run store and event serialisation stay out of the core |
| III. Typed and verified | OPEN: protocol attributes and generator-based `execute` must type-check structurally | PASS at design level: [contracts/protocols.py](contracts/protocols.py) passes mypy with the repository settings, and sample serial and asyncio runners written against it pass `mypy --strict` without casts or ignores |
| IV. Full support matrix | OPEN: timing criteria on Windows and macOS; lingering threads | PASS at design level: monotonic clock only; SC-006 makes the matrix explicit; blocking test tasks release at teardown. Runtime evidence remains an implementation gate |
| V. Executable docs | PASS: notebook, docs, changelog in scope | PASS at design level: [quickstart.md](quickstart.md) lists the notebook, the doc pages, the changelog entry and the regenerated `run.rst` |
| VI. Stable public API | OPEN: generator-task behaviour change; `run()` path rewritten internally | PASS at design level: every addition is a new name or a sibling protocol; `Task.start` and runner constructors stay call-compatible; the generator-task change is a recorded bug fix (spec Assumptions); Ctrl-C during `run()` keeps today's behaviour (R13) |

**Pre-research disposition:** three checks were open; research R2, R5, R9 and R13 and
the two mypy probes resolve them. No violation is accepted or waived.

**Post-design result:** PASS for task generation. `make tests` and the full matrix
remain required before implementation is complete.

## Design Decisions

### Run state

1. `RunContext` in `nornir/core/run.py` holds per-host state under one lock; first
   recording wins, later ones are dropped (R1, R6).
2. Recording a host that never started fires `task_instance_started` then
   `task_instance_completed` (FR-011). `cancel()` and the run deadline record pending
   hosts at once.
3. `AggregatedResult` keeps selection order; `results()` uses completion order.

### Runners

1. `StreamingRunner.execute(task, hosts, run) -> Iterator[None]` and
   `AsyncStreamingRunner.aexecute(task, hosts, run)`; `cancellation_depth` and
   `supports_background` are read-only properties (R2).
2. `ThreadedRunner.execute`: a pool without the context manager and a coordinator loop
   on `run.wait_for_change(next_deadline)` and `run.expire()`. When every host is
   recorded, it calls `shutdown(wait=False, cancel_futures=True)` (R7).
3. `SerialRunner.execute`: `yield from run.step_host(...)` for each host, checking the
   run deadline before each host.
4. `AsyncioRunner.aexecute`: semaphore as in spec 001, `call_at` timers for deadlines,
   a cancel callback that cancels running hosts' asyncio tasks after `RunContext` has
   recorded the reason (R8).
5. Each runner's existing `run()` / `arun()` drives its own `execute` / `aexecute` with
   a `RunContext` built from the runner options, so runner deadlines apply to `run()`
   (FR-024). `AsyncioRunner.arun` keeps the outer-cancellation drain of spec 001.

### Tasks

1. `task.checkpoint()`; subtask start and every `yield` are checkpoints (R4).
2. Interruptions subclass `BaseException`; subtasks re-raise them rather than wrapping
   them in `NornirSubTaskError`; the top-level task records them (R5).
3. Generator tasks are detected on the returned object, so wrappers work; one stepping
   driver serves `start()` and `SerialRunner` streams (R9).

### Entry points

1. Mode and capability checks before `_prepare_run` (R12).
2. Streams return a new iterator from `__iter__` / `__aiter__` that cancels when
   finalized early, plus `with` / `async with` (R10).
3. `_finalize_run` split so a background run keeps the exact order of `run()`, including
   no `task_completed` when `raise_on_error` raises (R12).

### Review flags

- **R9, generator tasks:** a task containing `yield` now runs. It ships as a bug fix in
  3.7.0, per the spec.

## Project Structure

### Feature artifacts

```text
specs/003-runner-streaming-cancellation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── protocols.py
│   ├── entry-points.md
│   └── errors.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks
```

### Implementation targets

```text
nornir/core/run.py                    # new: RunOptions, RunContext, handles, streams
nornir/core/task.py                   # PartialResult, checkpoint, stepping driver, interruption handling
nornir/core/__init__.py               # submit, run_stream, asubmit, astream; _finalize_run split
nornir/core/processor.py              # ProgressProcessor, Processors.task_instance_progress
nornir/core/exceptions.py             # TaskInterruptedError family, RunnerCapabilityError
nornir/core/plugins/runners.py        # StreamingRunner, AsyncStreamingRunner, CancellationDepth
nornir/plugins/runners/__init__.py    # execute/aexecute and deadline options on the three runners

tests/core/test_run_handle.py         # US1: submit, results, cancel, recording rules
tests/core/test_run_deadlines.py      # US2: deadlines on all runners, timing criteria
tests/core/test_run_progress.py       # US3: generator tasks, streams, progress processor
tests/core/test_run_contract.py       # protocols, capability errors, third-party fixture

docs/howto/long_running_tasks.ipynb   # executed notebook
docs/howto/index.rst                  # link the notebook
docs/plugins/execution_model.rst      # depth, SerialRunner differences, hook threads
docs/api/nornir/core/run.rst          # regenerated by make docs
CHANGELOG.rst                         # 3.7.0 entry
```

**Structure decision:** single library layout; one new core module because the run
objects are shared by `Nornir`, `Task` and the runners, and placing them in
`nornir/core/__init__.py` or `task.py` would create import cycles with the runner
protocols.

## Complexity Tracking

No constitution violation to justify.
