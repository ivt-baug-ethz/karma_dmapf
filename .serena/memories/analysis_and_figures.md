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
| `delay_evaluation.py` | 4 paper controllers (Karma = `NEGOTIATE_KARMA` at τ 0.1/0.15/0.25/0.5/0.75, baselines once) × 5×5/10 + 10×10/30, seeds 41–45, T=300, `ProcessPoolExecutor`; prints metric means and `negotiation_cases` totals | `delay_evaluation/tasks_grid{g}_agents{n}_T300.json` (metadata, summary rows, per-run metrics + `negotiation_cases` + per-task records `[agent_id, assigned, pickup, completed, min_pickup, min_task]`; + `runs/delay_evaluation_<ts>/`) | `Figure_5.py` → `Figure_5.png` | not yet (evaluation of the no-reset Karma and the delay metrics) |
| `karma_influence_sweep.py` | legacy τ × δ sweep incl. both Karma variants, T=1000, plots its own figures | nothing (`runs/karma_influence_sweep/`) | none | – |

Other entry points: `visualize_simulation.py` writes `results/animations/animation_<CTRL>.gif` (tracked)
from frames in `results/runs/visualize_simulation/`; `performance_tracking.py` only prints.

- Seeds are temporarily reduced to 41–45 in every analysis script (efficiency_benchmark,
  time_distribution, karma_influence, tradeoffs, delay_evaluation) for the 2026-09-27
  regeneration; the final paper numbers are to be run at 10 seeds (41–50; 41–60 for the τ sweeps).
- Measured wall times at 5 seeds, T = 100, 11 parallel jobs: efficiency_benchmark per
  controller: 5×5 13–35 s, 10×10 2–8 min, 15×15 11–22 min (egoistic 15×15: 100 min, the
  bottleneck). time_distribution per controller: 15×15/80 6–17 min (egoistic ≈ 55 min).
  karma_influence 15×15 ≈ 35 min with 5 workers.
- Gotcha: `karma_influence` / `karma_influence_tradeoffs` name their per-seed folder
  `results/runs/<script>_<YYYYmmdd_HHMMSS>` and combine *every* `seed*.json` in it. Two
  scenarios started in the same second therefore mix, which shows up as a zig-zag in Figure 3.
  Start parallel sweeps at least a second apart, or rebuild each summary from the per-seed files
  filtered by `agents{N}`.
- Throttling many single-core invocations from a zsh script: `jobs -r` is empty in a
  non-interactive zsh, so a `while (( $(jobs -r | wc -l) >= N ))` loop never waits. Use
  `xargs -P N` instead.
- Worker count: run the pooled scripts with `PYTHON_CPU_COUNT=12` (Python 3.13 honours it in
  `os.cpu_count()`), so at most 12 cores are used.
- The scripts are configured by editing module-level constants or the settings dict. There is no CLI.
  One scenario (time_distribution, karma_influence, tradeoffs) or one controller list
  (efficiency_benchmark) runs per invocation, so regenerating a figure means one run per grid
  (5/10, 10/30, 15/80) and, for time_distribution, per controller.
- `efficiency_benchmark` names its JSON after the *last* controller of the loop but stores all of them.
  Figure_1 expects one file per controller, so run it with one controller at a time
  (`mem:open_issues`).
- `karma_influence` keeps its own copy of `gini/summarize/compute_run_metrics` (service-time
  increase only). The others import `src.simulation.metrics`.
- The analyses and Figures 1–4 use `NEGOTIATE_KARMA` (no reset) as Karma. Since the 2026-09-27 regeneration every figure input exists
  for it. Stale `TRIP_KARMA` files from old runs are still in `efficiency_benchmark/` and
  `time_distribution/`, unused.
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
- All five share `figures/paper_style.py` for the controller styles (`mem:conventions`).
  The before/after evidence for that style (colour-blindness and greyscale previews, the raw
  renders, `palette_report.txt`) is kept in the git-ignored `results/archive/a11y_showcase/`. The
  script that produced it is deliberately not in the repo.
- Figure_5: 2×5 grid (rows 5×5/10, 10×10/30; cols: per-task task time, task delay, service time,
  per-agent cumulative delay at T as box plots, and the across-agent std of cumulative delay vs t,
  mean over seeds). Karma τ series are the Karma orange shaded light→dark with τ.
- CI (`figure-plots.yml`) renders all five and asserts `Figure_1..3.png`, `Figure_5.png` plus at least one
  `Figure_tradeoff_*.png`.

## Metrics (`src.simulation.metrics.compute_run_metrics`)

- Task time = `completed_time − assigned_time` (assignment → drop-off). "Reallocation" in the keys
  `"... Task Time (incl. Reallocation) (all agents)"` is the robot's drive from its pose at assignment
  to the pickup, which task time includes and service time does not. Waiting between spawn and
  assignment is deliberately excluded.
- Task delay = task time − (`minimum_pickup_time` + `minimum_task_time`), i.e. minus the
  unobstructed orientation-aware time pose-at-assignment → pickup → drop-off. 0 for an
  unobstructed trip (`mem:simulation/core`, step order). Keys `Avg/Std Task Delay (all agents)`.
- Cumulative agent delay = per-agent sum of task delays over its completed tasks (agents with at
  least one). Keys `Avg/Std/Gini Cumulative Delay (per agent)`. Idle detours are not included
  (`mem:simulation/negotiation`).
- Service time = `completed_time − pickup_time`.
- Service time increase (%) = (service − `minimum_task_time`) / `minimum_task_time` · 100.
- Aggregates: all-task mean/std/total, and per-agent means ("per agent mean").
- A* calls = the sum of the per-step counter.
- `summarize` → (mean, population std, median, Gini, IQR) across seeds.
- time_distribution writes raw per-task task times (from the assignment) and service times, without offset.
- Times are simulation steps; the figure axes label them "[s]".

## Key paper findings (for sanity-checking regenerated data)

**The numbers below are the original paper's.** They predate every fix in `mem:paper_changes`
(swap detection, pickups on pass-over, A* optimality, step order, the karma payment rules,
deadlock and id-bias fixes). The tracked `results/` were regenerated from the code on 2026-09-27
at 5 seeds, so they differ from these numbers. Throughput is higher, and every negotiation
controller is affected. Use the numbers below only as a rough orientation, not as exact targets.

- **Token passing**: fewest A* calls, fewest completed tasks, longest service time. At 15×15/80 it
  completes about 1.9k tasks with about 3k A* calls.
- **Egoistic**: the most A* calls (about 67k at 15×15/80) and the most completions.
- **Utilitarian and Karma**: about 33k A* calls, and service time about 15 vs 18 for token passing.
- **Service-time increase** (Fig. 4): token passing is about 43/44/70 %, egoistic about 39/33/45 %,
  and utilitarian about 22/23/33 % on 5/10/15. Karma equals utilitarian at τ=0 and rises with τ, to
  about 43 % at τ=1 on 15×15.
- **Karma vs the others**: same average efficiency as utilitarian, but the tightest spread (IQR and
  whiskers) of task and service times. That fairness effect is the paper's claim.
- **Stated limitations**: τ is studied only empirically. Other fairness notions, robustness and
  communication overhead are not studied.
- **Future work**: pay-to-society vs pay-to-peer payment, karma bounds, redistribution/reset schemes,
  convergence guarantees.
