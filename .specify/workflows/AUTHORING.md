# Authoring a solid Spec Kit workflow

Best practices for `.specify/workflows/<id>/workflow.yml`, collected from the upstream
authoring reference and publishing guide, from the practitioner literature on
spec-driven development, and from the one non-trivial workflow in this repository
(`implement-phased`). Written against Spec Kit **1.0.3**; check the version before
trusting a mechanical detail.

A workflow is solid when three things hold: a run that stops can be **resumed** without
redoing work, every claim of "done" is backed by a **mechanical check** rather than an
agent's own summary, and a human can **review the run** from its artifacts afterwards.
Most of the list below is one of those three in a specific place.

## Structure and metadata

1. **One workflow per directory, with a README next to it.** `workflow.yml` plus
   `README.md` documenting the step graph, every input, the state it writes, and the
   permissions its agents need. This is required for catalog submission and is what makes
   a workflow reviewable at all.
2. **Version the workflow and bump it on every behaviour change.** `workflow.version`
   is what an installed copy is compared against; a workflow whose behaviour drifts under
   a fixed version cannot be debugged from a run log.
3. **State a real `requires.speckit_version`.** Pin the first version whose engine
   behaviour you depend on, and say in a comment *why* that floor exists — see the note
   on `integration: "auto"` in `speckit/workflow.yml`. `requires` is advisory, not a
   runtime gate, so treat it as documentation for the reader, not enforcement.
4. **Keep `requires.integrations.any` a hint, not a closed set.** List what you tested;
   don't imply the workflow refuses others.
5. **Give every step an `id` that reads as a noun in a log line** (`select-group`,
   `final-gates`). Step ids are the primary handle in `state.json`, `log.jsonl`, overlays,
   and expressions. No colons — the engine reserves them for nesting.

## Inputs

6. **Every input gets a `prompt` written for someone who has never run the workflow**,
   including what the default does.
7. **Constrain with `enum` wherever the value set is finite.** This is both usability and
   the only real defence for a value that reaches a shell step.
8. **Default to the common case, and make the default discoverable.** `implement-phased`
   defaults `spec_dir` to the current feature, then the most recently modified
   `specs/*/tasks.md` — so the usual invocation is `-i` free.
9. **Make gate decisions pre-declarable with `verdict_input`.** An empty default prompts
   interactively; a supplied value runs unattended. One workflow then serves both the
   supervised first run and CI, with no second copy to keep in sync.
10. **Expose the model as an input, defaulted, and pass it to every agent step.** Cost and
    capability are run-time decisions, not authoring-time ones.
11. **Type inputs properly** (`number` for counts, `boolean` for flags) and bound the
    numbers you use as loop caps.

## Control flow

12. **Prefer many small steps over few clever ones.** Each step is a resume point and a
    log line; a step that does three things is a step you cannot resume into the middle of.
13. **Put logic in a script, not in expressions.** The expression language is deliberately
    small — `default`, `join`, `map`, `contains`, `from_json` over `inputs.*`,
    `steps.<id>.output.*`, `item`, `fan_in`, `context.run_id`, `context.workflow_dir`.
    Anything beyond a comparison belongs in a shell step that returns JSON.
14. **Always cap a loop.** `max_iterations` on `while` / `do-while`, and a `max_rounds`
    input for a validation loop, so a wedged agent burns a bounded amount of money.
15. **Make the loop condition depend on state on disk, not on an agent's claim.**
    `implement-phased` re-reads `tasks.md` in `select-group` each iteration, which is also
    why re-running the whole workflow on a half-finished feature is safe.
16. **Guard the loop body with an `if` on the selector's `found` flag.** A `do-while`
    always executes once; without the guard the last iteration runs against no work.
17. **Only reference steps that have already run**, and pass `| default('…')` on anything
    that may be absent.
18. **Use `fan-out` only for genuinely independent items**, with an explicit
    `max_concurrency`. Two agents editing the same file concurrently produces a conflict
    no downstream gate can untangle.

## Human gates

19. **Gate after every artifact a human would want to veto** — the spec, the plan, the
    group plan — and before anything destructive or privileged. That is the whole reason
    the engine has gates.
20. **Write the gate message as an instruction, not a label**: what to look at, and what
    each option will do next. "Review the group plan. approve starts the implementation
    loop; reject aborts."
21. **Show content with `show_file`, never by interpolating it into `message`.**
    `show_file` strips control characters; `message` does not, and agent- or
    user-supplied text in a prompt string is an injection surface.
22. **Know what `on_reject` does.** `abort` halts; `retry` pauses so the next `resume`
    re-runs the gate; `skip` merely means "don't abort" — it does **not** skip the
    following sibling steps. With `skip` you must branch on
    `steps.<gate>.output.choice` yourself.
23. **Turn a stop condition into a gate, not a failing step.** A failing shell step prints
    little more than an exit code. `implement-phased` routes preflight failures into a
    `preflight-stop` gate whose message is the problem *and* the fix.

## Agent steps

24. **Give an agent step a self-contained brief on disk and pass it the path.** Tasks
    verbatim, the checkpoint, the files to read first, the gate commands, the evidence
    rules. A prompt that has to be assembled from expressions cannot be inspected after
    the fact; a brief file is in the run directory forever.
25. **Scope each agent to one group of work and name the task IDs it owns**, with an
    explicit instruction not to start work belonging to another group.
26. **Tell the agent it is non-interactive.** "Nobody can answer questions: make routine
    decisions yourself and record them in your summary." Otherwise it stops to ask.
27. **Use a fresh agent per group rather than one long session.** Context that has
    accumulated three groups of debugging is worse at the fourth, and the literature on
    oversized context ("lost in the middle") applies to the agent as much as to the spec.
28. **Ground the agent in the repository before it generates.** The measured gain in
    *Spec Kit Agents* comes from a read-only discovery pass plus post-phase validation;
    the validation half mattered more than the discovery half.
29. **Set `timeout` deliberately** — the default is 300s, which no implementation agent
    will respect. `implement-phased` uses 10800.
30. **Put `continue_on_error: true` on agent steps.** A crashed or timed-out agent should
    be caught by the next mechanical gate, not kill the run. Note the flag covers returned
    failures only: an exception out of a step still aborts, and an operator's gate abort
    always wins.
31. **Document the tool grant the agents need.** `claude -p` denies anything it would
    normally prompt for, so an ungranted run fails at the first edit and reports the group
    as not done — a failure mode that looks like a workflow bug. Show the
    `SPECKIT_INTEGRATION_CLAUDE_EXTRA_ARGS` line or the settings allowlist in the README.

## Verification

32. **Separate generation from evaluation.** The agent that wrote the code never judges it.
    Use a fresh read-only reviewer, and prefer a different model when you can — self-
    evaluation bias is measurable.
33. **Run the mechanical gate first, the judge second.** Lint, types, tests, tree
    cleanliness and commit hygiene are cheap and objective; only spend a judge on a diff
    that already passes them.
34. **Use the repository's own gate commands** (`make ruff`, `make mypy`, `make pytest`,
    `make tests`), never a private reimplementation. A workflow with its own idea of green
    drifts away from CI silently.
35. **Check for gaming, not just for green.** Count new `# noqa` / `# type: ignore` without
    justification, require at least one commit since the group started, require every task
    ticked, require a clean tree. "Tests pass" is satisfiable by deleting tests.
36. **Give the judge the criteria by reference and demand a machine-readable verdict.**
    Point it at the brief, spec, plan, contracts and constitution, hand it the diff, and
    have it write `verdict.json` with `PASS`/`FAIL` plus findings. Prose verdicts cannot
    drive a loop.
37. **Feed findings back into a fix step, and validate the fix.** With `max_rounds = 3`:
    one implement attempt, up to two fix attempts, three validations — and the last fix is
    always validated. A fix round that is never re-checked is decoration.
38. **Have an explicit blocked state.** When the round cap is reached, surface a gate
    (`continue` leaves the group blocked and moves on; `abort` stops) rather than looping
    forever or silently proceeding.
39. **End with a whole-diff review and the full gate.** Per-group checks miss what only
    shows up in the assembled change — and the final gate is the one CI will run.

## Shell steps and state

40. **Treat a shell step as unsandboxed code running as the user.** No capability
    boundary, no `requires.permissions`.
41. **Never interpolate an unconstrained value into `run`.** Expressions are raw string
    substitution and there is no shell-escaping filter, so quoting is not a security
    boundary. Agent output is the worst case: branch on it with `if`/`switch`, or consume
    it inside a script, but keep it out of the command line.
42. **Only engine-controlled values belong in `run`.** In `implement-phased` that means
    `context.workflow_dir` and `context.run_id` and nothing else; the script reads the
    real inputs from the run's `inputs.json`. `SPECKIT_WORKFLOW_DIR` is available in the
    step environment for the same purpose.
43. **Collapse the shell steps into one script with subcommands.** One `phased.py` with
    `preflight` / `select` / `gates` / `check` / `final` / `summary` is testable, lintable
    and diffable; six inline `run:` blobs are none of those.
44. **Keep that script stdlib-only.** It runs before the environment is known good, and a
    dependency of the workflow engine is a dependency of every run.
45. **Return JSON from shell steps** (`output_format: json`) and branch on fields. Parsing
    human-readable output in an expression is how conditions silently become `false`.
46. **Pass agent → workflow data through files, not stdout.** The engine streams agent
    output without capturing it, so a shell step that reads `verdict.json`,
    `evidence.md`, `review.md` is the only reliable channel.
47. **Put all run state under the run directory and gitignore it.** `state.json`,
    `inputs.json`, `log.jsonl` are the engine's; put yours (ledger, briefs, gate logs,
    verdicts) alongside them. Then name the durable outputs explicitly — for
    `implement-phased`: the commits, the ticked checkboxes, and `implement-report.md`.
48. **Keep a ledger the run can be reconstructed from** — per-group status, rounds,
    commits, findings, history. It is what a resume reads and what a post-mortem reads.
49. **Make every step idempotent enough to be resumed into.** `specify workflow resume
    <run_id>` re-runs the paused or failed step; `--input` values merge over the stored
    ones. Say in the README which recoveries are supported (dirty tree, blown timeout).

## Distribution

50. **Use `slot` steps for the extension points you anticipate** and document what an
    overlay should fill them with. An unfilled slot is a no-op that returns
    `{slot: <name>}`, so downstream consumers must tolerate it.
51. **Customise an installed workflow with an overlay, never by editing it in place.**
    Overlays anchor on step ids (recursing into `then`/`else`/`steps`/`cases`), lower
    `priority` wins, and they cannot touch metadata, inputs, or fan-out templates.
    Inspect the result with `specify workflow resolve <id>`.
52. **Validate and dry-run before publishing.** `specify workflow info <path>` rejects a
    structurally invalid definition and prints the step graph; run the workflow end to end
    on a real feature; only then submit to a catalog.
53. **Audit any workflow you install before running it.** `info` shows metadata, not the
    `run:` fields that will execute. Read the YAML.

## The artifacts the workflow consumes

A workflow can only be as good as `spec.md`, `plan.md` and `tasks.md`, and these are the
practices that make those drivable by machine:

54. **Keep the spec short enough for a human to actually review.** AI-generated spec bloat
    is the most reported failure of spec-driven development: a spec nobody validates is
    auto-generated documentation, not a source of truth.
55. **Structure `tasks.md` as the workflow's unit of work.** Phase headings the selector
    can find, one checkbox per task, tasks sharing a file kept sequential, tests before
    the implementation they cover.
56. **End every phase with its own gate task and a `**Checkpoint**` line.** That line is
    what the validation loop judges against; a phase without one can only be checked for
    "no lint errors".
57. **Record what not to do in the constitution, not just what to do.** Prohibitions are
    what a judge needs to fail a diff that is otherwise green.
58. **Validate the plan before implementation, not after.** Cheapest place to catch drift,
    and the ablation results agree.

## Anti-patterns

- A single monolithic implement step for a whole feature; no group boundaries, no
  intermediate verification, nothing to resume into.
- Trusting an agent's own "all tasks complete" summary as the loop's exit condition.
- Interpolating a prompt step's output into a shell `run` field.
- An unbounded `while`, or a validation loop whose last fix is never re-checked.
- Gate messages that say "Continue?"
- A workflow-private notion of green that disagrees with `make tests`.
- Reimplementing in expressions what a ten-line Python subcommand does clearly.
- A `requires` block used as if it were a permission model.

## Sources

- [Workflow authoring reference](https://github.com/github/spec-kit/blob/main/docs/reference/workflows.md) — schema, step types, expressions, overlays, security rules
- [Workflow publishing guide](https://github.com/github/spec-kit/blob/main/workflows/PUBLISHING.md) — submission checklist and upstream best practices
- [Workflow system architecture](https://github.com/github/spec-kit/blob/main/workflows/ARCHITECTURE.md) — execution model, state persistence, resume
- [`workflows/speckit/workflow.yml`](https://github.com/github/spec-kit/blob/main/workflows/speckit/workflow.yml) — the reference gate-per-artifact workflow
- [Spec Kit Agents: Context-Grounded Agentic Workflows](https://arxiv.org/html/2604.05278v1) — discovery/validation hooks, judge separation, measured effect sizes
- [Best practices — intent-driven.dev](https://intent-driven.dev/knowledge/best-practices/) — reviewability, decomposition, continuous validation
- [Using spec-kit for a brownfield codebase (EPAM)](https://www.epam.com/insights/ai/blogs/using-spec-kit-for-brownfield-codebase) — early task-level review beats end-of-implementation review
- [Spec-driven development in practice](https://medium.com/@lookoutking/spec-driven-development-in-practice-my-experience-with-spec-kit-8f250b47d677) — spec bloat and curation
- `.specify/workflows/implement-phased/README.md` — the worked example in this repository
