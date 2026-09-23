# Analyses, log_files and figures

## Pipeline

| analysis script | what it runs | writes to `log_files/` | figure | paper |
|---|---|---|---|---|
| `_analysis_1_efficiency_benchmark.py` | `controllers` × `n_agents_map[grid]`, seeds 41–50, T=100, thread pool | `analysis_1/summary_{CTRL}_{grid}.json` (+ txt reports in `results/`) | `Figure_1.py` → `Figure_1.png` | Fig. 3 (benchmark vs #agents) |
| `_analysis_2_time_distribution.py` | one controller × one scenario, seeds 41–50, sequential | `analysis_2/all_{task,service}_times_{CTRL}_{grid}_{agents}.txt` | `Figure_2.py` → `Figure_2.png` | Fig. 5 (box plots) |
| `_analysis_3_karma_influence.py` | 4 paper controllers × τ 0.0–1.0 × seeds 41–60, one scenario, `multiprocessing.Pool` | `analysis_3/summary_grid{g}_agents{n}_T100.json` (+ per-seed JSONs in `results/figure3_karma_influence_<ts>/`) | `Figure_3.py` → `Figure_3.png` | Fig. 4 (service-time increase vs τ) |
| `_analysis_4_karma_influence_tradeoffs.py` | same as 3 but all `compute_run_metrics` metrics, `ProcessPoolExecutor` | `analysis_4/summary_grid{g}_agents{n}_T100.json` (+ `results/figure4_karma_influence_<ts>/`) | `Figure_4.py` → `Figure_tradeoff_<metric>.png/.pdf` | not in paper (supplementary) |
| `_analysis_4_karma_influence_sweep.py` | legacy τ × δ sweep incl. KARMA / ALTRUISTIC2, T=1000 | nothing (`results/karma_sweep/`) | none | – |

- The scripts are configured by editing module-level constants or the settings dict. There is no CLI.
  One scenario (analysis 2/3/4) or one controller list (analysis 1) runs per invocation, so
  regenerating a figure means one run per grid (5/10, 10/30, 15/80) and, for analysis 2, per
  controller.
- `_analysis_1` names its JSON after the *last* controller of the loop but stores all of them.
  Figure_1 expects one file per controller, so run it with one controller at a time
  (`mem:open_issues`).
- analysis 3 keeps its own copy of `gini/summarize/compute_run_metrics` (service-time increase only).
  The others import `analysis_helpers`.
- `log_files/analysis_2` also holds `KARMA` / `ALTRUISTIC2` files, and
  `analysis_3/summary_grid10_agents30_T100_TOLERANCES.json`. No figure reads them.

## Summary JSON schema (analysis 3/4)

`{"metadata": {grid_size_base, grid_size_env, n_agents, delta_threshold, influences, seeds,
controllers, …}, "summary": [{controller, karma_influence, delta_threshold, n_agents, grid_size,
metric, mean, std, median, gini, iqr, n_runs}], "raw": [...]}`. Non-karma controllers are run at
every τ too, where τ has no effect, which is why they plot as flat baselines.

analysis 1 JSON: `{grid: {CTRL: {n_agents: {metric: [mean, std, median, gini, iqr]}, "raw_data":
{n_agents: {metric: [per-seed values]}}}}}`, keys as strings. Figure_1 reads only `raw_data`.

## Figure scripts (`src_figures/`)

- Each has `main(output_dir, show)` plus argparse `--output-dir/-o` (default: the script dir,
  i.e. the committed `src_figures/Figure_N.png`) and `--no-show`. It switches to the Agg backend when
  `--no-show` is passed or under `GITHUB_ACTIONS`.
- Data paths are `Path(__file__).resolve().parent.parent / "log_files" / "analysis_N"`.
- Figure_1: a 3×4 grid (rows: grids 5/10/15; cols: completed tasks, A* calls, avg task time, avg
  service time). It smooths with a centred rolling median (window 3) and multiplies completed tasks
  and A* calls by the hard-coded per-grid `scale_factors`. Keep these unless told otherwise.
- CI (`figure-plots.yml`) renders all four and asserts `Figure_1..3.png` plus at least one
  `Figure_tradeoff_*.png`.

## Metrics (`analysis_helpers.compute_run_metrics`)

- Task time = `completed_time − spawned_time`, i.e. it includes waiting for assignment
  ("incl. Reallocation").
- Service time = `completed_time − pickup_time`.
- Service time increase (%) = (service − `minimum_task_time`) / `minimum_task_time` · 100.
- Aggregates: all-task mean/std/total, and per-agent means ("per agent mean").
- A* calls = the sum of the per-step counter.
- `summarize` → (mean, population std, median, Gini, IQR) across seeds.
- analysis_2 writes raw per-task times with **+1** added (inclusive count).
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
