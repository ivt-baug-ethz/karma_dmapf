#!/usr/bin/env bash
# Stop hook: ensure pylint reports no errors before finishing.
#
# Mirrors the gate CI enforces (`pylint src --errors-only` in .github/workflows/lint.yml).
# Fires only when Python files have uncommitted changes (staged, unstaged or untracked)
# and blocks when pylint reports any error-category message, so a broken import or a bad
# call cannot slip out unnoticed. Self-terminating: once the errors are fixed (or the .py
# changes are reverted or committed), the condition is false and Claude stops normally.
#
# Style-category messages are deliberately NOT enforced here: the existing codebase carries
# a large backlog of them, so a full-score gate would block every session.
set -euo pipefail

repo="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$repo"

# Only run when Python files have uncommitted changes - otherwise nothing to check.
status="$(git status --porcelain --untracked-files=all 2>/dev/null || true)"
py_changed="$(printf '%s\n' "$status" | grep -E '\.py$' || true)"
[ -z "$py_changed" ] && exit 0

# Need the project's pinned pylint; skip silently if the venv is not set up.
pylint="$repo/venv/bin/pylint"
[ -x "$pylint" ] || exit 0

[ -d src ] || exit 0

report="$("$pylint" src --errors-only 2>&1 || true)"
errors="$(printf '%s\n' "$report" | grep -cE '^[^ ]+\.py:[0-9]+:[0-9]+: E[0-9]+' || true)"

[ "$errors" -eq 0 ] && exit 0

# Keep the blocking reason short; the agent re-runs the command to see the detail.
cat <<JSON
{"decision":"block","reason":"pylint reported ${errors} error(s). Run './venv/bin/pylint src --errors-only', fix each one (or add a scoped, justified disable), then finish. This is the same gate CI enforces."}
JSON
exit 0
