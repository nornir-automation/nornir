# Data Model: Runner Streaming, Cancellation, and Timeouts

**Feature**: 003-runner-streaming-cancellation | [Plan](plan.md) | [Types](contracts/protocols.py)

All state lives in memory, for one run, in one process.

## Generator tasks

- A `def` generator task's `return` value is its final result.
- An `async def` generator cannot `return` a value, so it ends by yielding its final
  `Result`. A `def` generator may do the same. The driver closes the generator after a
  yielded `Result`.
- Any other yielded value that is not a `PartialResult` is wrapped in one.

## PartialResult (new, `nornir.core.task`)

| Field | Type | Rule |
|---|---|---|
| `host` | `Host` | The host that reported it |
| `result` | `Any` | Free value: a message, a dict |
| `progress` | `float \| None` | None, or 0 ≤ value ≤ 1; otherwise `ValueError` |
| `name` | `str \| None` | Set by the driver to the yielding task's name |

Never stored in `MultiResult`; never sets a host as failed (FR-032).

## RunOptions (new, `nornir.core.run`)

Frozen dataclass: `per_host_timeout`, `timeout`, each `None` or a positive finite number
of seconds. Effective value = per-run field if not `None`, else runner field (FR-025).

## RunContext (new, `nornir.core.run`)

One per run. Holds:

- the run's `Task`, the selected hosts in selection order, effective `RunOptions`;
- `run_deadline: float | None` (monotonic), set when the run starts;
- `cancel_reason: InterruptReason | None`;
- per-host state (below), keyed by host name;
- `completed: list[Result]`, final top-level results in completion order;
- `latest: dict[str, PartialResult]`;
- subscriber callbacks, change callbacks and cancel callbacks;
- one `threading.Lock` and one `threading.Condition` built on it.

### Per-host state (private)

| Field | Meaning |
|---|---|
| `status` | `pending` → `running` → `recorded`, or `pending` → `recorded` |
| `task` | The task copy, set when the host starts or when it is recorded without running |
| `started_at` | Monotonic time when the host started |
| `deadline` | `min(started_at + per_host_timeout, run_deadline)`, or `None` |
| `interruption` | `TaskInterruptedError` instance once interrupted; read by `checkpoint()` |
| `results` | The recorded `MultiResult` |

### Transitions

```text
pending  --start_host / step_host / astart_host-->  running
pending  --cancel()-->                              recorded (TaskCancelledError, started=False)
pending  --run deadline (expire)-->                 recorded (TaskTimeoutError scope=run, started=False)
running  --task returns or fails-->                 recorded (task's own Result)
running  --cancel(), then checkpoint or asyncio cancel-->  recorded (TaskCancelledError, started=True)
running  --deadline, then expire() or checkpoint-->        recorded (TaskTimeoutError, started=True)
recorded --any later result-->                      unchanged (dropped)
```

`cancel()` on a `running` host sets `interruption` only. On `checkpoint` runners, the
host is recorded when its task reaches a checkpoint. On `immediate` runners, the runner
cancels the asyncio task at once. `expire()` records a running host directly, without
waiting for a checkpoint, so `ThreadedRunner` returns on time (FR-022).

The run is **finished** when every host is `recorded`. Finalization then builds the
`AggregatedResult` in selection order and applies the `raise_on_error`, `failed_hosts`
and `task_completed` rules of R12.

## RunHandle / AsyncRunHandle (new, `nornir.core.run`)

Wrap one `RunContext` plus: `id`, the driving thread or asyncio task, the finalized
`AggregatedResult` or the internal error, and a `done` event. No other state; in
particular, no partial result except `latest` (FR-008).

## RunStream / AsyncRunStream (new, `nornir.core.run`)

Wrap one handle and one subscription created before the first host starts, plus an
`iterated` flag for single use.

## Interruption errors (new, `nornir.core.exceptions`)

See [contracts/errors.md](contracts/errors.md).

## Existing entities

| Entity | Change |
|---|---|
| `Task` | Gains `checkpoint()`, a private host-state reference passed to subtasks, the private stepping driver `_start_steps`. `start()`, `astart()`, `run()`, `arun()` signatures unchanged |
| `Result`, `MultiResult`, `AggregatedResult` | Unchanged |
| `Processor` | Unchanged; `ProgressProcessor` is a sibling protocol |
| `Processors` | Gains `task_instance_progress` |
| `RunnerPlugin`, `AsyncRunnerPlugin` | Unchanged |
| `SerialRunner`, `ThreadedRunner`, `AsyncioRunner` | Gain `per_host_timeout`, `timeout`, `cancellation_depth`, `execute`/`aexecute`; `ThreadedRunner` and `SerialRunner` gain `supports_background` |
| `Nornir` | Gains `submit`, `run_stream`, `asubmit`, `astream`; private `_finalize_run` split in two |
