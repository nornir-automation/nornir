A previous agent implemented the group "$heading"
of $spec_dir and validation round
$round failed. Fix exactly what the findings name,
make the gates green again, and commit. Nobody can answer questions.

Findings (read first): $findings
Brief with the task list, gates, evidence rules and "Read first" files:
$brief

Rules:
1. Address every finding. Do not make a failing test pass by weakening it; fix
   the code. If a test contradicts spec.md or the contracts, fix the test to
   match the spec and say so in the evidence file.
2. Re-run the gates listed in the brief until green. No new lint or type ignore
   without a comment saying why.
3. Tick the group's task IDs to [X] in tasks.md once they are truly done.
4. Append evidence for any test you added or changed, as the brief describes.
5. Commit with Conventional Commits subjects; clean tree; never amend, push, or
   open a pull request.
6. Finish with a summary under 150 words: finding -> what you changed, commit
   SHAs.
