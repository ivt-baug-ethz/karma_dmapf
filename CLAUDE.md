@AGENTS.md

# Claude Code specifics

Everything above is shared with all agents. This part covers only what is specific to Claude Code.

## Harness

- Serena is registered per project and launched with `--project`, so it is **already activated** when the session starts. There is no setup step and no `activate_project` call; that tool is not exposed. Its tools are named `mcp__serena__*`. Use them for memories and semantic code work by default, without being prompted.
- `.claude/settings.json` denies `EnterWorktree`, `git worktree`, `git commit` and `git stash`, and pins `worktree.bgIsolation: none`. If some harness default tries to move you into a worktree, stay in the main checkout instead.
- Stop hooks enforce the definition of done (details in the `task_completion` memory):
  - the memory check and `pylint --errors-only` block the turn
  - the `results/` regeneration reminder shows the user a non-blocking message

  Never work around a blocking hook by stashing or committing.

## Use serena's tools (they are faster and cheaper than reading files)

- **Locate code**: `get_symbols_overview` for a file's symbol map, `find_symbol` (`depth=1` for a class's methods, `include_info=True` for signature + docstring, `include_body=True` only when you must see the implementation). Reading all of `environment.py` to find one method is the wrong move.
- **Plain-text search and file reads** use the native `Grep` / `Glob` / `Read` tools. This serena runs in the `ide-assistant` context, which omits `search_for_pattern`, `read_file`, `list_dir` and `find_file` precisely because the harness already has faster equivalents.
- **Before changing any signature or removing anything**: `find_referencing_symbols`. The negotiation functions share a call site in `Environment.make_decision`, and every analysis script duplicates the simulation loop, so a change there ripples widely.
- **Edit**: `replace_symbol_body` for a whole function/method, `replace_content` (regex or literal) for a few lines inside one, `replace_in_files` for the same edit across many files (`dry_run` first), `rename_symbol` / `safe_delete_symbol` for reference-aware refactors. These return success only when applied; do not re-read the file to confirm.
- **Memories**: `list_memories`, `read_memory`, `write_memory`, `edit_memory`.
- **Note**: serena line numbers are **0-based**; the Read tool's are 1-based.
- Batch independent serena calls in one message. The server serialises them internally, so there is no race, and it saves round-trips.
