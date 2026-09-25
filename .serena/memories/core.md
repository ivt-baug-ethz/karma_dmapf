# karma_dmapf — core

Research code (Python 3.13) for **Karma mechanisms in decentralised, cooperative MAPF**. It
simulates a lifelong, orientation-aware warehouse pickup-and-delivery (MAPD) scenario on a square
grid and compares conflict-resolution controllers: token passing, egoistic/utilitarian negotiation,
Karma negotiation, and centralised CBS. It also produces the paper's evaluation data and figures.
Not a library: there is no `pyproject.toml` / `setup.py`, nothing is installed, and there are no tests.

## Source map

| path | contents |
|---|---|
| `src/simulation/environment.py` | `Environment`: settings dict, spawning, task assignment/closing, per-controller route planning incl. the negotiation loop (`mem:simulation/core`, `mem:simulation/negotiation`) |
| `src/simulation/agent.py` | `Agent`: position/orientation/status/route, route execution, cost-to-change, karma balance and its per-trip reset |
| `src/simulation/task.py` | `Task`: random pickup/delivery cells, spawn/pickup/completion times, `minimum_task_time` |
| `src/simulation/negotiation_strategy.py` | `NegotiationStrategy`: egoistic / utilitarian / karma decision rules and the karma payment rule |
| `src/simulation/geometry.py` | `Grid` (occupancy, random free cells), `GridTools` (3-D reservation table, vertex/edge conflict detection), `Geometry` (manhattan + rotation estimate) |
| `src/simulation/constants.py` | agent statuses/orientations, `DIRS`, spawn borders, the `MAPF_CONTROLLER_*` strings |
| `src/simulation/metrics.py` | `gini`, `summarize`, `compute_run_metrics`, shared by the efficiency benchmark and the tradeoff/sweep scripts |
| `src/simulation/visualization.py` | matplotlib grid + reservation-table frames (Agg backend), `make_gif` via imageio |
| `src/planners/astar.py` | `AStarPathPlanner` over (x, y, θ, t) with a reservation grid, `PathPlannerState`, the thread-local A* call counter |
| `src/planners/cbs.py` | `Planner_CBS`, used only by the `CENTRALIZED` controller |
| `src/planners/assignment.py` | Hungarian agent↔task assignment (`scipy.optimize.linear_sum_assignment`) |
| `src/scripts/` | entry points: the four analyses and the legacy sweep (`mem:analysis_and_figures`), `visualize_simulation` (GIF rendering) and `performance_tracking` (quick 10-seed printout) |
| `figures/Figure_N.py` | paper figures, rendered from `results/<analysis>/` to `figures/Figure_N.png`; CI renders them |
| `figures/paper_style.py` | the shared controller colours, markers and hatches (colour-blind and greyscale safe) |
| `results/<analysis>/` | committed analysis outputs, i.e. the figure inputs; one folder per analysis script, named after it |
| `results/animations/` | committed README GIFs; `visualize_simulation` writes here |
| `results/runs/` | git-ignored; every script's automatic intermediate output (per-seed JSONs, txt reports, GIF frames, sweep cache) |
| `results/archive/` | git-ignored; manual copies of old runs, incl. everything the old `results/` scratch held |

## Project-wide invariants

- **Imports rooted at the repo root**: `src` is a namespace package (no `__init__.py`) holding the
  packages `simulation` and `planners`, imported absolutely with the `src.` prefix
  (`from src.simulation.agent import Agent`, `from src.planners.astar import AStarPathPlanner`),
  with `TYPE_CHECKING` guards for cycles. Scripts run from the repo root with the venv active and
  `export PYTHONPATH=.`; nothing is installed and `sys.path` is never touched. pylint needs the
  same `PYTHONPATH=.` (CI, hook); Pylance/pyright resolve from the workspace root without config. `figures/` never imports `src/`.
- **Outputs are anchored at the repo root** (`Path(__file__).resolve().parent.parent` / `os.path`
  equivalent), never cwd-relative. Figure inputs go to `results/<analysis>/` and run output goes to `results/runs/`.
- **The tracked `results/` must correspond to the current code.** It is regenerable (runs are deterministic
  per seed), but the analyses are slow. **Never re-run them unasked**: remind the user instead
  (`mem:task_completion`).
- **Grid padding**: scripts state the base grid (5/10/15) and pass `grid_size = base + 2`. Tasks spawn
  only off the 1-cell border (`SPAWN_BORDER`), while agents may spawn and drive on it. Filenames and
  metadata use the *base* size.
- **Paper scenarios**: base grid 5/10/15 with 10/30/80 agents, T = 100 steps.
  Seeds: 41–50 in the efficiency benchmark and time distribution, 41–60 in the karma influence analyses.
- **Controllers**: all eight keep code support, but evaluations and figures use only the four paper
  controllers. Never add another controller to a script that does not already run it
  (`mem:simulation/negotiation`).
- Agent instructions have one source each:
  - `AGENTS.md` holds the shared rules for all agents: project overview, hard rules, working protocol.
  - `CLAUDE.md` is `@AGENTS.md` plus Claude-only harness and serena usage.
  - `.github/copilot-instructions.md` only points to `AGENTS.md`.
  - Conventions, commands and design notes live in these memories only.

  Change a rule in exactly one of these places, never in two.

## Harness wiring (`.claude/`)

- Serena is registered as a **project-scoped** MCP server in `~/.claude.json` (not as a plugin) and
  launched with `--project <repo> --context ide-assistant`, so it comes up already activated. There
  is no `activate_project` step, and that tool is not exposed. Tools are named `mcp__serena__*`.
  The `ide-assistant` context also omits `search_for_pattern`, `read_file`, `list_dir` and
  `find_file`; use the harness's native `Grep` / `Glob` / `Read` for those.
- `hooks/serena-session-start.sh` (SessionStart) restates that workflow.
- Stop hooks:
  - `hooks/serena-memory-reminder.sh` and `hooks/pylint-check.sh` block the turn (`mem:task_completion`).
  - `hooks/results-regeneration-reminder.sh` never blocks; it shows a `systemMessage` naming the analyses whose `results/<analysis>/` are stale.
- Worktrees are disabled (`worktree.bgIsolation: none` plus a deny rule), so work happens directly in
  the checked-out branch. `git commit` and `git stash` are denied; the user owns both.
  Analysis scripts are deliberately not allow-listed.

## Where to look next

- `mem:simulation/core`: step loop, agent/task lifecycle, orientation-aware A* and reservation grid, conflict detection, CBS, assignment, RNG and the thread-local A* counter.
- `mem:simulation/negotiation`:
  - controller table and negotiation protocol
  - cost-to-change and cost transform
  - Karma rule, payment and reset
  - paper ↔ code naming
- `mem:analysis_and_figures`:
  - what each analysis runs and writes, and the `results/` filename schema
  - which figure reads what, and which paper figure it is
  - metric definitions and key paper findings
- `mem:open_issues`: known bugs and planned refactors (shared simulation runner, controller support).
- `mem:tech_stack`: interpreter and pinned dependencies.
- `mem:conventions`: code style, imports, script layout, figure-script CLI, lint rules, commits.
- `mem:suggested_commands`: commands for venv, lint, format, running analyses and figures on macOS.
- `mem:task_completion`: quality gates before a task is done, incl. the Stop hooks.
