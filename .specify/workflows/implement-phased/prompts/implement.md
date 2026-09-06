You are implementing one group of tasks for a Spec Kit feature in this repository,
non-interactively. Nobody can answer questions: make routine decisions yourself and
record them in your final summary.

Brief (self-contained, read it first): $brief
Group: $heading (group $index of $total)
Task IDs in scope: $ids. Implement ONLY these; do not
start tasks that belong to other groups.

Rules:
1. Read every file under "Read first" in the brief, then the tasks. AGENTS.md and the
   constitution are binding. You may invoke the speckit-implement skill scoped to these
   task IDs; if you do, treat its checklist gate as already cleared by this workflow and
   do not create or modify ignore files.
2. Work through the tasks in their listed order; tasks that share a file stay sequential.
   Test tasks come before the implementation they cover: run them, see them fail, then
   make them pass.
3. Run the quality gates listed in the brief and iterate until they are green. Never add
   a lint or type ignore without a comment saying why. Never hand-edit notebook output;
   re-execute notebooks instead.
4. Tick every task ID of this group to [X] in tasks.md when it is done. If a task cannot
   be completed, leave it [ ] and explain why in the evidence file.
5. Append test evidence to the evidence file exactly as the brief describes.
6. Commit all work with Conventional Commits subjects (feat:, fix:, test:, docs:,
   chore:). The working tree must be clean when you finish. Never amend an existing
   commit, never push, never open a pull request.
7. Finish with a summary under 200 words: one line per task ID (done / partial /
   blocked + reason), the commit SHAs you produced, and decisions worth flagging.
