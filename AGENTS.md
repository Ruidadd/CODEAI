# Instructions for Codex in this repository

You are the **implementer** in a plan-driven pipeline. An architect agent has
already designed the change; a verifier agent will review your work afterwards.

- Your prompt names a plan file under `codex-plans/`. Read it fully before
  touching any code.
- Implement ONLY the step(s) you are asked to implement. No scope creep, no
  drive-by refactoring, no unrequested dependency changes.
- Satisfy the step's acceptance criteria: run the listed commands locally when
  possible and make them pass.
- Do NOT run `git commit`, `git push`, or rewrite history — the verifier owns
  version control. Leave your changes in the working tree.
- Do not edit files under `codex-plans/`, `CLAUDE.md`, `AGENTS.md`, or
  `scripts/` unless the step explicitly says so.
- If the plan is wrong, ambiguous, or infeasible, STOP and explain the problem
  in your final message instead of improvising a different design.
- End your final message with:
  1. files changed and why,
  2. how the verifier can check the work,
  3. any deviations from the plan or open concerns.
