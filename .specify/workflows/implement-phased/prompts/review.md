Review the complete change set of feature $spec_dir:
`git diff $base_sha...HEAD`. Criteria: spec.md and plan.md in
that directory, .specify/memory/constitution.md, AGENTS.md. Use the code-review skill at high
effort if it is available; otherwise review the diff yourself: correctness bugs first, then
contract and constitution violations, then test quality.

Write the findings to $state_dir/review.md as a table:
severity (high/medium/low) | file:line | summary | fixed or deferred.
Fix every high-severity finding: edit, run `make ruff`, `make mypy` and the relevant
`make pytest ARGS="..."`, commit with a Conventional Commits subject. Leave lower severities
as deferred. Clean tree when done. Never amend, push, or open a pull request. If there is
nothing at high severity, say so in review.md and change nothing.
