# CODEAI — Fable × Codex collaboration protocol

This repository uses a three-role pipeline for implementation work:

| Role | Agent | Responsibility |
|------|-------|----------------|
| Architect (动脑) | Claude (Fable) | Explore the codebase, design the solution, write the plan |
| Implementer (干活) | OpenAI Codex CLI | Execute plan steps and write the code |
| Verifier (验收) | Claude Code | Review the diff, run tests, accept or reject |

## Rules for Claude in this repository

- For non-trivial implementation tasks, prefer the `/codex-run` pipeline over
  writing all the code yourself. Trivial edits (typos, one-liners, docs) can be
  done directly.
- Plans live in `codex-plans/*.md`, one file per task, following
  `codex-plans/TEMPLATE.md`. Steps must be independently implementable and each
  must carry concrete acceptance criteria (commands + expected results).
- Delegate execution with:
  `bash scripts/codex-exec.sh <plan-file> "<instruction, e.g. Implement step 2>"`
- Send verification feedback to the same Codex session with:
  `bash scripts/codex-exec.sh --resume "<precise feedback>"`
- After every Codex run, ALWAYS verify before moving on: review `git diff`
  against the plan, run the step's acceptance-criteria commands, and check for
  scope creep.
- Maximum 3 feedback rounds per step. If Codex still fails, implement the fix
  yourself and record the takeover in the plan's Feedback log.
- Claude owns git: Codex never commits (AGENTS.md forbids it). Commit only
  after acceptance passes, with a message describing the change itself, not the
  pipeline.
- If `codex` is not installed or not logged in, tell the user to run
  `npm install -g @openai/codex && codex login` — do not silently fall back to
  doing the implementation yourself unless the user agrees.
