#!/usr/bin/env bash
# Stop hook: keep the serena memories current.
#
# Serena memories (.serena/memories/) are the project's only knowledge store. Fires
# when the working tree has changes OUTSIDE them (and outside noise / .serena config)
# but no memory was refreshed this session, and asks Claude to update the memories
# before finishing.
#
# Freshness is judged by FILE MTIME rather than git state, so it also works while the
# memory updates are still uncommitted: memories are considered current when a memory
# file was modified at least as recently as the newest real work file. Self-terminating:
# once a memory is updated (or the work is committed), the condition is false and Claude
# stops normally.
set -euo pipefail

repo="${CLAUDE_PROJECT_DIR:-$(pwd)}"
# --untracked-files=all so git lists each untracked file with its full path.
status="$(git -C "$repo" status --porcelain --untracked-files=all 2>/dev/null || true)"

# Not a git repo, or a clean tree: nothing to enforce.
[ -z "$status" ] && exit 0

# Real "work" changes: exclude the memories, .serena config, and .DS_Store noise.
work="$(printf '%s\n' "$status" | grep -vE '\.serena/|\.DS_Store' | grep -vE '^[[:space:]]*$' || true)"

# Only memories/noise changed (or everything committed): fine.
[ -z "$work" ] && exit 0

mtime() {  # epoch mtime of a file, 0 if missing (BSD stat, GNU fallback)
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0
}

# Newest mtime among the real work files (strip the git status XY prefix, and
# take the destination path for renames "old -> new").
work_mtime=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  path="${line:3}"
  path="${path##* -> }"
  file="$repo/$path"
  [ -f "$file" ] || continue
  t="$(mtime "$file")"
  [ "$t" -gt "$work_mtime" ] && work_mtime="$t"
done <<EOF
$work
EOF

# Newest mtime among the memory files.
track_mtime=0
while IFS= read -r file; do
  [ -z "$file" ] && continue
  t="$(mtime "$file")"
  [ "$t" -gt "$track_mtime" ] && track_mtime="$t"
done <<EOF
$(find "$repo/.serena/memories" -type f -name '*.md' 2>/dev/null)
EOF

# Memories touched at least as recently as the latest work change: up to date.
[ "$track_mtime" -ge "$work_mtime" ] && [ "$track_mtime" -gt 0 ] && exit 0

cat <<'JSON'
{"decision":"block","reason":"There are uncommitted changes but no serena memory was updated this session. Per CLAUDE.md, the memories are the project's only knowledge store: use serena's write_memory to update whichever memories the change affects (structure -> core, style -> conventions, commands -> suggested_commands, domain details -> the topic memory). If the changes genuinely warrant no memory update, say so explicitly in your summary and touch nothing (or commit the work), then finish."}
JSON
exit 0
