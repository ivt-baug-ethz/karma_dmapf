# Definition of done

Run in this order from the repo root with the venv active:

1. `black src figures`: CI fails on any formatting diff (`psf/black@stable`).
2. `PYTHONPATH=. ./venv/bin/pylint src --errors-only` must report nothing. This is the gate in CI and locally.
3. If `figures/` or anything they read changed, render all five figures into a scratch dir
   (`mem:suggested_commands`). `figure-plots.yml` fails if one of them errors.
4. If simulation code changed, run a short smoke simulation of the touched controller(s) with
   `check_violation` (`src/scripts/visualize_simulation.py` pattern, small grid, few steps), not a full
   analysis. There is no test suite.
5. **Regeneration reminder.** If a change touches `src/` simulation code or an analysis script, the
   affected `results/<analysis>/` are stale. Do **not** re-run them on your own. End the final
   summary with a reminder naming the analyses (and scenarios) to regenerate, and offer to run them.
   Mapping:
   - `simulation/` and `planners/` modules → all five analyses (incl. `delay_evaluation`)
   - `scripts/<analysis>.py` → that analysis
   - `simulation/visualization.py`, `visualize_simulation`, `performance_tracking` and the legacy
     sweep → none

   Once the user agrees, regenerate them and re-render the figures.
6. Update the serena memories whose content changed (`write_memory`):
   - structure → `mem:core`
   - style → `mem:conventions`
   - commands → `mem:suggested_commands`
   - domain details → the topic memory
   - resolved or new known problems → `mem:open_issues`

   A stale memory is a bug and is fixed in the same task.

## Stop hooks

Three hooks in `.claude/settings.json` run at the end of every turn:

- `pylint-check.sh` runs step 2 whenever `.py` files have uncommitted changes, and **blocks** on errors.
- `serena-memory-reminder.sh` **blocks** when work files are newer than every file in
  `.serena/memories/`, i.e. when step 6 was skipped.
- `results-regeneration-reminder.sh` **never blocks**. It shows the user a `systemMessage` for step 5
  while `src/**/*.py` has uncommitted changes and an affected `results/<analysis>/` has none. Any
  uncommitted edit, even a path-only one, triggers it until the work is committed or the results are
  regenerated.

The blocking hooks are self-terminating: satisfy the condition (or commit the work) and they pass.

`serena-memory-reminder.sh` compares **mtimes**, and its work set is
`git status --porcelain --untracked-files=all` minus `.serena/` and `.DS_Store`. Any *untracked*
file therefore counts. A PDF or scratch file dropped into the repo root becomes the newest work file
and blocks the turn even when the memories are genuinely current. Since `git commit` is denied, the
fix is to `.gitignore` or move the stray file and then touch a memory, not to argue with the hook.
The hook's own advice to "say so explicitly and touch nothing" does not stop it: it checks only
mtimes, so it keeps blocking every turn until a memory file is newer than the newest work file or
the work is committed.

`git commit` and `git stash` are denied by the permission settings. Never try to work around a
blocking hook by stashing or committing. Leave both to the user; finish the work in the tree.
