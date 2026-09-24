# Analyses, results and figures

## Pipeline

Scripts live in `src/scripts/` and run from the repo root with `export PYTHONPATH=.`
(`python src/scripts/<name>.py`).
Each analysis writes its figure inputs to the tracked `results/<name>/` and its intermediate output
to the git-ignored `results/runs/`. The figure number is the only numbering; the scripts are named.

| analysis script | what it runs | writes to tracked `results/` | figure | paper |
|---|---|---|---|---|
| `efficiency_benchmark.py` | `controllers` × `n_agents_map[grid]`, seeds 41–50, T=100, thread pool | `efficiency_benchmark/summary_{CTRL}_{grid}.json` (+ txt reports and PDFs in `runs/efficiency_benchmark/`) | `Figure_1.py` → `Figure_1.png` | Fig. 3 (benchmark vs #agents) |
| `time_distribution.py` | one controller × one scenario, seeds 41–50, sequential | `time_distribution/all_{task,service}_times_{CTRL}_{grid}_{agents}.txt` | `Figure_2.py` → `Figure_2.png` | Fig. 5 (box plots) |
| `karma_influence.py` | 4 paper controllers × τ 0.0–1.0 × seeds 41–60, one scenario, `multiprocessing.Pool` | `karma_influence/summary_grid{g}_agents{n}_T100.json` (+ per-seed JSONs in `runs/karma_influence_<ts>/`) | `Figure_3.py` → `Figure_3.png` | Fig. 4 (service-time increase vs τ) |
| `karma_influence_tradeoffs.py` | same as karma_influence but all `compute_run_metrics` metrics, `ProcessPoolExecutor` | `karma_influence_tradeoffs/summary_grid{g}_agents{n}_T100.json` (+ `runs/karma_influence_tradeoffs_<ts>/`) | `Figure_4.py` → `Figure_tradeoff_<metric>.png/.pdf` | not in paper (supplementary) |
| `karma_influence_sweep.py` | legacy τ × δ sweep incl. KARMA / ALTRUISTIC2, T=1000, plots its own figures | nothing (`runs/karma_influence_sweep/`) | none | – |

Other entry points: `visualize_simulation.py` writes `results/animations/animation_<CTRL>.gif` (tracked)
from frames in `results/runs/visualize_simulation/`; `performance_tracking.py` only prints.

- The scripts are configured by editing module-level constants or the settings dict. There is no CLI.
  One scenario (time_distribution, karma_influence, tradeoffs) or one controller list
  (efficiency_benchmark) runs per invocation, so regenerating a figure means one run per grid
  (5/10, 10/30, 15/80) and, for time_distribution, per controller.
- `efficiency_benchmark` names its JSON after the *last* controller of the loop but stores all of them.
  Figure_1 expects one file per controller, so run it with one controller at a time
  (`mem:open_issues`).
- `karma_influence` keeps its own copy of `gini/summarize/compute_run_metrics` (service-time
  increase only). The others import `src.simulation.metrics`.
- `results/time_distribution` also holds `KARMA` / `ALTRUISTIC2` files. They have the same format
  and the script still produces them when that controller is selected, but no figure reads them.
  A former `..._TOLERANCES.json` of karma_influence came from a code variant that no longer exists
  and is in `results/archive/`.

## Summary JSON schema (karma_influence, tradeoffs)

`{"metadata": {grid_size_base, grid_size_env, n_agents, delta_threshold, influences, seeds,
controllers, …}, "summary": [{controller, karma_influence, delta_threshold, n_agents, grid_size,
metric, mean, std, median, gini, iqr, n_runs}], "raw": [...]}`. Non-karma controllers are run at
every τ too, where τ has no effect, which is why they plot as flat baselines.

efficiency_benchmark JSON: `{grid: {CTRL: {n_agents: {metric: [mean, std, median, gini, iqr]}, "raw_data":
{n_agents: {metric: [per-seed values]}}}}}`, keys as strings. Figure_1 reads only `raw_data`.

## Figure scripts (`figures/`)

- Each module docstring states which files it reads and how to regenerate them (script + constants per run).
- Each has `main(output_dir, show)` plus argparse `--output-dir/-o` (default: the script dir,
  i.e. the committed `figures/Figure_N.png`) and `--no-show`. It switches to the Agg backend when
  `--no-show` is passed or under `GITHUB_ACTIONS`.
- Data paths are `Path(__file__).resolve().parent.parent / "results" / "<analysis>"`.
- Figure_1: a 3×4 grid (rows: grids 5/10/15; cols: completed tasks, A* calls, avg task time, avg
  service time). It smooths with a centred rolling median (window 3) and multiplies completed tasks
  and A* calls by the hard-coded per-grid `scale_factors`. Keep these unless told otherwise.
- All four share `figures/paper_style.py` for the controller styles (`mem:conventions`).
  The before/after evidence for that style (colour-blindness and greyscale previews, the raw
  renders, `palette_report.txt`) is kept in the git-ignored `results/archive/a11y_showcase/`. The
  script that produced it is deliberately not in the repo.
- CI (`figure-plots.yml`) renders all four and asserts `Figure_1..3.png` plus at least one
  `Figure_tradeoff_*.png`.

## Metrics (`src.simulation.metrics.compute_run_metrics`)

- Task time = `completed_time − spawned_time`, i.e. it includes waiting for assignment
  ("incl. Reallocation").
- Service time = `completed_time − pickup_time`.
- Service time increase (%) = (service − `minimum_task_time`) / `minimum_task_time` · 100.
- Aggregates: all-task mean/std/total, and per-agent means ("per agent mean").
- A* calls = the sum of the per-step counter.
- `summarize` → (mean, population std, median, Gini, IQR) across seeds.
- time_distribution writes raw per-task times with **+1** added (inclusive count).
- Times are simulation steps; the figure axes label them "[s]".

## Key paper findings (for sanity-checking regenerated data)

- **Token passing**: fewest A* calls, fewest completed tasks, longest service time. At 15×15/80 it
  completes about 1.9k tasks with about 3k A* calls.
- **Egoistic**: the most A* calls (about 67k at 15×15/80) and the most completions.
- **Altruistic and Karma**: about 33k A* calls, and service time about 15 vs 18 for token passing.
- **Service-time increase** (Fig. 4): token passing is about 43/44/70 %, egoistic about 39/33/45 %,
  and altruistic about 22/23/33 % on 5/10/15. Karma equals altruistic at τ=0 and rises with τ, to
  about 43 % at τ=1 on 15×15.
- **Karma vs the others**: same average efficiency as altruistic, but the tightest spread (IQR and
  whiskers) of task and service times. That fairness effect is the paper's claim.
- **Stated limitations**: τ is studied only empirically. Other fairness notions, robustness and
  communication overhead are not studied.
- **Future work**: pay-to-society vs pay-to-peer payment, karma bounds, redistribution/reset schemes,
  convergence guarantees.
