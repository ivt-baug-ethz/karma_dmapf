#!/usr/bin/env bash
# SessionStart hook: state the serena workflow that applies to every turn in this repository.
#
# The serena MCP server is registered per project and launched with --project, so it comes up
# already activated — there is nothing to call before work starts. This hook exists to make the
# usage rules part of the session context rather than something the user has to repeat.
set -euo pipefail

repo="${CLAUDE_PROJECT_DIR:-$(pwd)}"

if [ ! -d "$repo/.serena/memories" ]; then
  echo "SERENA: no memories found at .serena/memories — run the serena 'onboarding' tool."
  exit 0
fi

cat <<'EOF'
SERENA IS ACTIVE — the MCP server is already attached to this project. Do not call
activate_project; it is not exposed. Its tools are named mcp__serena__*.

Use it without being asked, on every task:
1. Start by reading the memories: list_memories, then read_memory "core" — the graph root that
   maps src/ and links to every other memory. Follow only the links the task needs.
2. Navigate code symbolically: get_symbols_overview for a file's symbol map, find_symbol for a
   definition (depth=1 for a class's methods, include_body=True only when the implementation
   matters), find_referencing_symbols before changing any signature or deleting anything.
   Do not read a whole module to find one method.
3. Edit symbolically: replace_symbol_body, replace_content, replace_in_files, rename_symbol,
   safe_delete_symbol.
4. Plain-text search and file reads use the native Grep / Glob / Read tools — this serena runs in
   the ide-assistant context, which deliberately omits its own search_for_pattern / read_file.
5. Serena memories are this project's only knowledge store. Update them via write_memory or
   edit_memory as part of finishing a task; a stale memory is a bug.
EOF
