#!/usr/bin/env bash
# Dispatch one work order to the Codex CLI (non-interactive implementer).
#
# Usage:
#   scripts/codex-exec.sh <plan-file> "<instruction>"        start a new session
#   scripts/codex-exec.sh --resume "<feedback>"              continue the last session
#
# Environment:
#   CODEX_MODEL   optional model override (e.g. gpt-5.5-codex); otherwise the
#                 user's ~/.codex/config.toml default is used.
set -euo pipefail

usage() {
  sed -n '2,8p' "$0" >&2
  exit 2
}

if ! command -v codex >/dev/null 2>&1; then
  echo "error: codex CLI not found. Install and authenticate first:" >&2
  echo "  npm install -g @openai/codex && codex login" >&2
  exit 127
fi

repo_root="$(git rev-parse --show-toplevel)"
out_dir="$repo_root/.codex-out"
mkdir -p "$out_dir"

args=(
  --sandbox workspace-write
  --cd "$repo_root"
  --output-last-message "$out_dir/last-message.txt"
  --color never
)
if [ -n "${CODEX_MODEL:-}" ]; then
  args+=(-m "$CODEX_MODEL")
fi

if [ "${1:-}" = "--resume" ]; then
  feedback="${2:-}"
  [ -n "$feedback" ] || usage
  codex exec resume --last "${args[@]}" "$feedback"
else
  plan_file="${1:-}"
  instruction="${2:-}"
  { [ -n "$plan_file" ] && [ -n "$instruction" ]; } || usage
  if [ ! -f "$repo_root/$plan_file" ] && [ ! -f "$plan_file" ]; then
    echo "error: plan file not found: $plan_file" >&2
    exit 1
  fi
  codex exec "${args[@]}" - <<EOF
You are the implementer in this repository's pipeline; AGENTS.md defines your role.
Plan file: ${plan_file}
Work order: ${instruction}
Read the plan file first, implement only what the work order covers, satisfy its
acceptance criteria, and do not commit.
EOF
fi

echo
echo "--- codex final message (.codex-out/last-message.txt) ---"
cat "$out_dir/last-message.txt" 2>/dev/null || echo "(no final message captured)"
