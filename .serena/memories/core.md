# karma_dmapf — core

Research code (Python 3.13) for **Karma mechanisms in decentralised, cooperative MAPF**. It
simulates a lifelong, orientation-aware warehouse pickup-and-delivery (MAPD) scenario on a square
grid and compares conflict-resolution controllers: token passing, egoistic/altruistic negotiation,
Karma negotiation, and centralised CBS. It also produces the paper's evaluation data and figures.
Not a library: there is no `pyproject.toml` / `setup.py`, nothing is installed, and there are no tests.

## Source map

| path | contents |
|---|---|
| `src/environment.py` | `Environment`: settings dict, spawning, task assignment/closing, per-controller route planning incl. the negotiation loop (`mem:simulation/core`, `mem:simulation/negotiation`) |
| `src/agent.py` | `Agent`: position/orientation/status/route, route execution, cost-to-change, karma balance and its per-trip reset |
| `src/task.py` | `Task`: random pickup/delivery cells, spawn/pickup/completion times, `minimum_task_time` |
| `src/negotiation_strategy.py` | `NegotiationStrategy`: egoistic / altruistic / karma decision rules and the karma payment rule |
| `src/planner_path_astar.py` | `AStarPathPlanner` over (x, y, θ, t) with a reservation grid, `PathPlannerState`, the thread-local A* call counter |
| `src/planner_mapf_central_CBS.py` | `Planner_CBS`, used only by the `CENTRALIZED` controller |
| `src/planner_assignment_central.py` | Hungarian agent↔task assignment (`scipy.optimize.linear_sum_assignment`) |
| `src/geometry.py` | `Grid` (occupancy, random free cells), `GridTools` (3-D reservation table, vertex/edge conflict detection), `Geometry` (manhattan + rotation estimate) |
| `src/constants.py` | agent statuses/orientations, `DIRS`, spawn borders, the `MAPF_CONTROLLER_*` strings |
| `src/analysis_helpers.py` | `gini`, `summarize`, `compute_run_metrics`, shared by analysis 1 and the tradeoff/sweep scripts |
| `src/_analysis_N_*.py` | evaluation scripts that write `log_files/analysis_N/` (`mem:analysis_and_figures`) |
| `src/_example_*.py` | GIF rendering (`_example_visualize_simulation`) and a quick 10-seed performance printout |
| `src/visualization.py` | matplotlib grid + reservation-table frames (Agg backend), `make_gif` via imageio |
| `src_figures/Figure_N.py` | paper figures, rendered from `log_files/`; CI renders them |
| `log_files/analysis_N/` | committed analysis outputs, i.e. the figure inputs |
| `animations/` | committed README GIFs |
| `results/`, `figs/`, `src/results/` | git-ignored scratch |

## Project-wide invariants

- **Flat imports**: `src/` modules import each other as top-level modules (`from agent import Agent`),
  with `TYPE_CHECKING` guards for cycles. Run `src/` scripts with cwd `src/`. pylint and
  `pyrightconfig.json` (`extraPaths: ["src"]`) resolve them. `src_figures/` never imports `src/`.
- **Outputs are anchored at the repo root** (`Path(__file__).resolve().parent.parent` / `os.path`
  equivalent), never cwd-relative. Figure inputs go to `log_files/analysis_N/` and scratch goes to `results/`.
- **`log_files/` must correspond to the current code.** It is regenerable (runs are deterministic
  per seed), but the analyses are slow. **Never re-run them unasked**: remind the user instead
  (`mem:task_completion`).
- **Grid padding**: scripts state the base grid (5/10/15) and pass `grid_size = base + 2`. Tasks spawn
  only off the 1-cell border (`SPAWN_BORDER`), while agents may spawn and drive on it. Filenames and
  metadata use the *base* size.
- **Paper scenarios**: base grid 5/10/15 with 10/30/80 agents, T = 100 steps.
  Seeds: 41–50 in analysis 1/2, 41–60 in analysis 3/4.
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
  - `hooks/results-regeneration-reminder.sh` never blocks; it shows a `systemMessage` naming the analyses whose `log_files/` are stale.
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
  - what each analysis runs and writes, and the `log_files/` filename schema
  - which figure reads what, and which paper figure it is
  - metric definitions and key paper findings
- `mem:open_issues`: known bugs and planned refactors (repo restructure, controller support).
- `mem:tech_stack`: interpreter and pinned dependencies.
- `mem:conventions`: code style, imports, script layout, figure-script CLI, lint rules, commits.
- `mem:suggested_commands`: commands for venv, lint, format, running analyses and figures on macOS.
- `mem:task_completion`: quality gates before a task is done, incl. the Stop hooks.
