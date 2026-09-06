# implement-phased

A Spec Kit workflow that executes a feature's `tasks.md` **one group at a time**, each group in
a fresh agent, with a **validation loop** that has to pass before the next group starts.

```text
preflight ─ plan-review gate ─┬─ select-group ─ implement ─┬─ gates ─ judge ─ check ─ fix ─┐ ─ blocked gate ─┐
                              │                            └──── repeat while check.retry ──┘                 │
                              └───────────────────── repeat while a group is pending ─────────────────────────┘
review ─ final-gates ─ summary ─ report
```

Groups are the `## Phase N:` sections of `tasks.md`. Each phase in the tasks template ends with
its own "run the gates until green" task and a `**Checkpoint**` line, which is what the loop
validates against.

## Per-group cycle

| Step | Kind | What it does |
|---|---|---|
| `select-group` | shell | Picks the first phase with unticked tasks that is not blocked; writes a self-contained brief (tasks verbatim, checkpoint, context files, gate commands, evidence rules) under the run directory. |
| `implement` | agent | Fresh `claude -p` session (auto permissions, `prompts/implement.md`) implementing only that group's task IDs, ticking them, committing with Conventional Commits. |
| `gates` | shell | Mechanical gate: every task ticked, at least one commit since group start, Conventional subjects, clean tree, `make ruff`, `make mypy`, scoped `make pytest`, no new `# noqa` / `# type: ignore` without a comment. |
| `judge` | agent | Only when the gates pass. Read-only reviewer that gets the criteria by reference (brief, spec, plan, contracts, constitution) and the group diff, and writes `verdict.json` (PASS/FAIL + findings). |
| `check` | shell | Merges gate failures and judge findings into `findings.md`; decides `retry` (another round) or `blocked` (round cap reached). |
| `fix` | agent | Only when `retry`. Fresh session that fixes exactly the findings, re-runs gates, commits. |
| `blocked` gate | human | Only when the group is still failing after the last round: `continue` leaves it blocked and moves on, `abort` stops the run. |

With `max_rounds=3` a group gets one implement attempt, up to two fix attempts, and three
validations; the last fix is always validated.

## Tail

`review` (whole-diff review, high-severity findings fixed and committed), `final-gates`
(`make tests`, `docs/api` drift recorded), `summary` (writes `summary.txt` with the
`STATUS: DONE|INCOMPLETE | SPEC_DIR: … | REASON: …` line), `report` (writes and commits
`<spec-dir>/implement-report.md`, prints the summary).

## Run

```bash
# interactive: prompts at the plan gate and at any blocked group
specify workflow run implement-phased -i spec_dir=specs/001-asyncio-runner

# unattended: pre-decide both gates
specify workflow run implement-phased \
  -i spec_dir=specs/001-asyncio-runner -i plan_verdict=approve -i blocked_verdict=continue

# resume a paused or failed run (e.g. after cleaning a dirty tree)
specify workflow resume <run_id>
```

Inputs: `spec_dir` (default: current feature from `.specify/feature.json`, else the most recently
modified `specs/*/tasks.md`), `max_rounds` (1-5, default 3), `guidance` (free text forwarded to
every implement agent), `plan_verdict`, `blocked_verdict`, and `model` (default
`opus`; passed to every agent step as `--model`, so implementation, judge, fix, review and report
all run on it; override with `-i model=sonnet`).

Agent steps run `claude -p --permission-mode auto --model <model>` directly from `phased.py`,
with the prompt rendered from `prompts/<step>.md`. Nothing has to be configured up front: no
environment variable, no `.claude/settings.json`. Auto mode approves routine tool calls (edits,
`make`, `git add`/`commit`, `uv`) on its own and, in a headless session, denies rather than
prompts for anything it judges risky. A denied or crashed agent does not fail the run: the next
mechanical gate reports what is missing and the fix round picks it up. Every agent's full output
is kept in `agent-<step>-<time>.log` under the run state directory and its final message is
echoed on the terminal.

## State

Everything the loop needs lives in `.specify/workflows/runs/<run_id>/phased/` (gitignored):
`ledger.json` (per-group status, rounds, commits, findings, history), `brief-<group>.md`,
`gates-<group>-r<n>.log`, `verdict.json`, `findings.md`, `evidence.md`, `review.md`,
`final-gates.log`, `summary.txt`. The only durable outputs are the commits the agents make,
the ticked checkboxes in `tasks.md`, and `implement-report.md`.

Re-running the workflow on the same feature is safe: `select-group` reads progress from
`tasks.md`, so finished phases are skipped and a blocked one is retried from scratch.

## Design notes

- Every step is a subcommand of one stdlib-only script, `phased.py` (`preflight`, `select`,
  `gates`, `check`, `final`, `summary`, and `agent <name>`). It never interpolates user input;
  workflow inputs are read from the run's `inputs.json`. Only engine-controlled values
  (`context.workflow_dir`, `context.run_id`) appear in `run:` fields.
- Agent steps are `shell` steps rather than spec-kit `prompt` steps so the workflow can set the
  permission mode and the model itself; spec-kit's `prompt` step offers neither. Agent → workflow
  data goes through files (`verdict.json`, `evidence.md`, `review.md`) that later steps read.
- Gate commands are the repository's own (`make ruff`, `make mypy`, `make pytest ARGS=…`,
  `make tests`, see `AGENTS.md`). The scoped pytest paths come from the group's own
  `make pytest ARGS="…"` task when it has one, else from the `tests/…` paths its tasks mention.
- An agent step always exits 0 and records the agent's exit code in the ledger: a crashed or
  timed-out agent is caught by the next mechanical gate instead of killing the run.
