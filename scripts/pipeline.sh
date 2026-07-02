#!/usr/bin/env bash
# One-command local workflow: Fable plans -> Codex implements -> CC verifies.
#
# Usage:
#   scripts/pipeline.sh "<task description>"     full run: plan -> execute -> verify -> accept
#   scripts/pipeline.sh --plan <plan-file>       run an existing plan (skip the planning phase)
#
# Requirements: claude CLI (logged in), codex CLI (logged in), git, clean working tree.
# Environment:
#   CC_MODEL      optional model for the claude calls (default: your claude default)
#   CODEX_MODEL   optional model for codex (consumed by scripts/codex-exec.sh)
#   MAX_ROUNDS    rework rounds per step before aborting for human takeover (default 3)
set -euo pipefail

usage() {
  sed -n '2,7p' "$0" >&2
  exit 2
}

die() {
  echo "pipeline: $*" >&2
  exit 1
}

banner() {
  echo
  echo "════════════════════════════════════════════════════════"
  echo "  $*"
  echo "════════════════════════════════════════════════════════"
}

[ $# -ge 1 ] || usage

command -v claude >/dev/null 2>&1 || die "claude CLI not found (npm install -g @anthropic-ai/claude-code)"
command -v codex  >/dev/null 2>&1 || die "codex CLI not found (npm install -g @openai/codex && codex login)"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [ -n "$(git status --porcelain)" ] && [ "${PIPELINE_ALLOW_DIRTY:-0}" != "1" ]; then
  die "working tree is dirty; commit or stash first (verification reviews git diff). Override with PIPELINE_ALLOW_DIRTY=1"
fi

MAX_ROUNDS="${MAX_ROUNDS:-3}"
mkdir -p .codex-out
log_file=".codex-out/pipeline-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee "$log_file") 2>&1
echo "pipeline log: $log_file"

# Headless Claude call. Bash is allowed so the verifier can run tests and the
# acceptor can commit — this workflow assumes a trusted local repository.
cc() {
  local extra=()
  [ -n "${CC_MODEL:-}" ] && extra=(--model "$CC_MODEL")
  claude -p "$1" \
    --permission-mode acceptEdits \
    --allowedTools "Bash,Read,Edit,Write,Glob,Grep" \
    "${extra[@]}"
}

# ── Phase 1: PLAN ────────────────────────────────────────────────────────────
if [ "${1:-}" = "--plan" ]; then
  plan_file="${2:-}"
  [ -n "$plan_file" ] || usage
  [ -f "$plan_file" ] || die "plan file not found: $plan_file"
  banner "Phase 1 — PLAN: using existing $plan_file"
else
  task="${1:-}"
  [ -n "$task" ] || usage
  slug="$(printf '%s' "$task" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' \
          | sed 's/^-//; s/-$//' | cut -c1-40)"
  plan_file="codex-plans/$(date +%Y%m%d-%H%M)-${slug:-task}.md"

  banner "Phase 1 — PLAN (Claude, architect) → $plan_file"
  cc "You are the architect in this repository's pipeline (see CLAUDE.md).
Task: ${task}

Explore the codebase as needed, then write an implementation plan to ${plan_file}
following codex-plans/TEMPLATE.md exactly: goal, context/constraints, numbered
'### Step N:' sections that are each independently implementable, and per-step
acceptance criteria as runnable commands with expected results.
Write ONLY the plan file. Do not implement anything else."

  [ -f "$plan_file" ] || die "planning phase did not produce $plan_file"
fi

total_steps="$(grep -c '^### Step' "$plan_file" || true)"
[ "$total_steps" -gt 0 ] || die "no '### Step N:' sections found in $plan_file"
echo "plan has $total_steps step(s)"

# ── Phases 2+3: EXECUTE (Codex) + VERIFY (Claude) per step ──────────────────
for ((n = 1; n <= total_steps; n++)); do
  banner "Phase 2 — EXECUTE step $n/$total_steps (Codex, implementer)"
  bash scripts/codex-exec.sh "$plan_file" "Implement step $n"

  round=0
  while true; do
    banner "Phase 3 — VERIFY step $n/$total_steps (Claude, acceptance gate)"
    verdict="$(cc "You are the verifier in this repository's pipeline (see CLAUDE.md).
Verify step $n of the plan ${plan_file}:
1. Review 'git diff' (and untracked files) against the plan — correctness, scope creep.
2. Run that step's acceptance-criteria commands and check the results.
Do not fix anything yourself.

Your reply MUST end with exactly one final line:
PASS
or
FAIL: <one precise, actionable sentence for the implementer>" | tee /dev/stderr)"

    last_line="$(printf '%s\n' "$verdict" | sed -e 's/\r$//' | grep -v '^[[:space:]]*$' | tail -n 1)"
    case "$last_line" in
      PASS*)
        echo "step $n: PASS"
        break
        ;;
      FAIL:*)
        round=$((round + 1))
        if [ "$round" -gt "$MAX_ROUNDS" ]; then
          die "step $n still failing after $MAX_ROUNDS rework rounds — human/CC takeover needed. Feedback: ${last_line#FAIL: }"
        fi
        banner "Phase 2 — REWORK step $n, round $round/$MAX_ROUNDS (Codex)"
        bash scripts/codex-exec.sh --resume "Step $n verification failed: ${last_line#FAIL: } Fix this; stay within the plan's scope."
        ;;
      *)
        die "verifier ended with an unrecognized verdict line: $last_line"
        ;;
    esac
  done
done

# ── Phase 4: ACCEPT ──────────────────────────────────────────────────────────
banner "Phase 4 — ACCEPT (Claude, final acceptance + commit)"
cc "You are the verifier in this repository's pipeline (see CLAUDE.md).
All steps of ${plan_file} passed per-step verification. Now:
1. Run the plan's full acceptance suite one last time on the final state.
2. Fill in the plan's 'Acceptance record' section (steps passed, rounds, takeovers).
3. Commit ALL changes (implementation + plan file) with a message describing the
   change itself, not the pipeline. Do not push."

banner "DONE — pipeline complete. Log: $log_file"
git log --oneline -1
