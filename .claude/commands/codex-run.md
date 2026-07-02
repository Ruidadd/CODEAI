---
description: Fable 规划 → Codex 实现 → CC 验收 的三段式流水线
argument-hint: <任务描述>
---

Task: $ARGUMENTS

Run the three-phase pipeline defined in CLAUDE.md. Do not write the
implementation code yourself unless a takeover is triggered in Phase 3.

## Phase 1 — PLAN (you, the architect)

1. Explore the codebase as needed to understand the task.
2. Write a plan to `codex-plans/<yyyymmdd>-<slug>.md` following
   `codex-plans/TEMPLATE.md`: goal, context/constraints, numbered steps that
   are each independently implementable, and per-step acceptance criteria as
   runnable commands with expected results.
3. If the task is large or ambiguous, show the plan to the user before
   executing; otherwise proceed.

## Phase 2 — EXECUTE (Codex, the implementer)

For each step N, in order:

```
bash scripts/codex-exec.sh codex-plans/<plan-file>.md "Implement step N"
```

Read Codex's final message before verifying. If Codex reports the plan is
infeasible, go back to Phase 1 and revise the plan instead of forcing it.

## Phase 3 — VERIFY (you, the acceptance gate)

After each step:

1. Review `git diff` against the plan — correctness, scope creep, style.
2. Run the step's acceptance-criteria commands (tests / build / lint).
3. PASS → mark the step done in the plan file, continue to the next step.
   FAIL → append the failure to the plan's Feedback log, then:

```
bash scripts/codex-exec.sh --resume "<precise, actionable feedback>"
```

Maximum 3 feedback rounds per step; after that, fix it yourself and record the
takeover in the Feedback log.

## Phase 4 — ACCEPT

1. Run the full acceptance suite one last time on the final state.
2. Fill in the plan's Acceptance record (what passed, rounds needed, takeovers).
3. Commit everything (implementation + plan file) with a message describing
   the change itself.
4. Report to the user: the plan, how many Codex rounds each step took, and the
   verification results.
