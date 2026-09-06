Write the implementation report for feature $spec_dir to
$spec_dir/implement-report.md, then commit it.

Sources (facts only, invent nothing): the ledger
$state_dir/ledger.json (groups, rounds, status, commits,
findings, history), $state_dir/evidence.md,
$state_dir/review.md, the full gate log
$final_log, the summary $summary,
and tasks.md in the spec directory.

Sections, in order:
1. Header: feature, base commit $base_sha, head commit,
   groups passed/blocked, run status $status.
2. Group ledger table: group, tasks, validation rounds, judge verdict, commit SHAs, status.
3. Tasks not completed, with the reason from the ledger findings ("None" if empty).
4. Local-pass evidence: one row per test from evidence.md; a test visible in the diff but
   absent from evidence.md gets `MISSING — see <group>` in its "passed at" cell.
5. Gate output: the final lines of the full gate log.
6. Review findings from review.md, marked fixed or deferred.
7. Decisions worth revisiting: blocked groups, round-cap hits, fixes that changed tests.
8. Next steps; when the status is INCOMPLETE the first step is the one that clears it
   (for example: rerun `specify workflow run implement-phased` after fixing the blocked group).

Commit only the report, with the subject `docs: add implementation report for <feature>`.
Never push. The working tree must be clean afterwards. As your final message print the
content of $summary verbatim, ending with its STATUS line.
