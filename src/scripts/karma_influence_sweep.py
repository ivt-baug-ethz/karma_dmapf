"""Parameter sweep for Karma MAPF negotiation.

This script varies karma influence and delta threshold settings and runs all
available decentralized policies on a 5x5 grid (with the existing +2 padding).
Aggregated summaries and figures are written to <repo>/results/runs/karma_influence_sweep/.
"""

from __future__ import annotations

import copy
import json
import logging
import multiprocessing
from time import perf_counter
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pathlib import Path
from tqdm import tqdm
from typing import Any, Dict, Iterable, List, Tuple


from src.simulation.constants import (
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
)
from src.simulation.environment import Environment
from src.planners.astar import AStarPathPlanner
from src.simulation.metrics import summarize, compute_run_metrics

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Sweep knobs (adjust here for deeper or faster runs)
GRID_SIZE_BASE = 5
# Agent counts selected per grid size (keep 5-grid scenario unchanged)
AGENTS_BY_GRID: Dict[int, List[int]] = {
    5: [6, 8, 10],  # [6, 8, 10],  # max 10
    # 10: [10, 20, 30],  # max 30
    # 15: [10, 40, 80],  # max 80
    # 20: [15, 50, 130, 180],  # max 180
}
AGENT_COUNTS = AGENTS_BY_GRID[GRID_SIZE_BASE]
RANDOM_SEEDS = [41, 42, 43, 44, 45, 46, 47, 48, 49, 50]
KARMA_INFLUENCES = [0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
DELTA_THRESHOLDS = [0.5]  # [0.5, 1.5]
RECOMPUTE_RESULTS = True  # set to False to load cached CSV/JSON and skip reruns

# Output locations
OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "results" / "runs" / "karma_influence_sweep"
)
FIGS_DIR = OUTPUT_DIR / "figs"
RUNS_JSON = OUTPUT_DIR / "runs.json"
SEED_RESULTS_DIR = OUTPUT_DIR / "seed_runs"

# Controllers under test
ALL_CONTROLLERS = [
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
]
KARMA_CONTROLLERS = [
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
]

BASE_SIMULATION_SETTINGS: Dict[str, Any] = {
    "time_horizon_visualization": 10,
    "time_simulation_duration": 1000,
    "params_astar": {
        "max_iterations": 1e5,
        "planning_horizon": 50,
        "planning_horizon_buffer": 20,
    },
    "params_cbs": {
        "max_iterations": 5000,
        "MAX_IDLE_TIME_CONSIDERED": 5,
        "PLANNING_HORIZON": 100,
    },
    "params_karma": {
        "initial_karma": 20,
        "delta_threshold": 0,
        "karma_payment": 1,
        "karma_influence": 0.2,
    },
    "debug_statements": False,
}

METRICS_OF_INTEREST = [
    "A* Calls",
    "Completed Tasks",
    "Total Task Time (incl. Reallocation) (all agents)",
    "Avg Task Time (incl. Reallocation) (all agents)",
    "Std Task Time (incl. Reallocation) (all agents)",
    "Total Service Time (all agents)",
    "Avg Service Time (all agents)",
    "Std Service Time (all agents)",
    "Avg Service Time Increase (%) (all agents)",
    "Avg Service Time (per agent mean)",
    "Avg Service Increase (%) (per agent mean)",
    "Avg Task Delay (all agents)",
    "Std Task Delay (all agents)",
    "Avg Cumulative Delay (per agent)",
    "Std Cumulative Delay (per agent)",
    "Gini Cumulative Delay (per agent)",
]

# Focused metric sets to keep figure counts small and targeted
LINE_METRICS = [
    "Completed Tasks",
    "Avg Service Time (all agents)",
    "Avg Service Time Increase (%) (all agents)",
    "Avg Service Time (per agent mean)",
    "Avg Service Increase (%) (per agent mean)",
]

CONTROLLER_COMPARISON_METRICS = [
    "Completed Tasks",
    "Avg Service Time (all agents)",
    "Avg Service Time Increase (%) (all agents)",
    "Avg Service Increase (%) (per agent mean)",
]


def _sanitize_float(value: float) -> str:
    return str(value).replace(".", "p")


def _run_seed_job(args: Tuple[str, float, float, int, int]) -> Dict[str, Any]:
    controller, karma_influence, delta_threshold, n_agents, seed = args
    settings = copy.deepcopy(BASE_SIMULATION_SETTINGS)
    settings.update(
        {
            "random_seed": seed,
            "grid_size": GRID_SIZE_BASE + 2,
            "n_agents": n_agents,
            "mapf_control": controller,
        }
    )
    settings["params_karma"]["karma_influence"] = karma_influence
    settings["params_karma"]["delta_threshold"] = delta_threshold
    start_ts = perf_counter()
    metrics = run_single_simulation(settings)
    duration_sec = perf_counter() - start_ts
    logger.info(
        "\nSeed run finished | ctrl=%s agents=%d influence=%.2f delta=%.2f seed=%d duration=%.2fs",
        controller,
        n_agents,
        karma_influence,
        delta_threshold,
        seed,
        duration_sec,
    )
    return {
        "controller": controller,
        "karma_influence": karma_influence,
        "delta_threshold": delta_threshold,
        "n_agents": n_agents,
        "seed": seed,
        "metrics": metrics,
        "duration_seconds": duration_sec,
    }


def _seed_result_path(result: Dict[str, Any]) -> Path:
    fname = (
        f"seed{result['seed']}_ctrl{result['controller']}_"
        f"inf{_sanitize_float(result['karma_influence'])}_"
        f"delta{_sanitize_float(result['delta_threshold'])}_"
        f"agents{result['n_agents']}.json"
    )
    return SEED_RESULTS_DIR / fname


def _save_seed_result(result: Dict[str, Any]) -> None:
    SEED_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    _seed_result_path(result).write_text(json.dumps(result, indent=2))


def run_single_simulation(simulation_settings: Dict[str, Any]) -> Dict[str, float]:
    env = Environment(settings=simulation_settings)
    for _ in range(simulation_settings["n_agents"]):
        env.spawn_agent()
    for _ in range(simulation_settings["n_agents"]):
        env.spawn_task()

    n_astar_calls = 0
    for _ in tqdm(
        range(env.settings["time_simulation_duration"]),
        total=env.settings["time_simulation_duration"],
        desc="Sim time steps",
    ):
        env.step()
        n_astar_calls += AStarPathPlanner.get_counter()
        AStarPathPlanner.reset_counter()

    return compute_run_metrics(env.completed_tasks, n_astar_calls)


def run_configuration(
    controller: str,
    karma_influence: float,
    delta_threshold: float,
    n_agents: int,
    random_seeds: Iterable[int],
) -> Tuple[Dict[str, Tuple[float, float, float, float, float]], Dict[str, List[float]]]:
    metrics_lists: Dict[str, List[float]] = {
        metric: [] for metric in METRICS_OF_INTEREST
    }
    for seed in random_seeds:
        logger.info(
            "Seed run | ctrl=%s agents=%d influence=%.2f delta=%.2f seed=%d",
            controller,
            n_agents,
            karma_influence,
            delta_threshold,
            seed,
        )
        settings = copy.deepcopy(BASE_SIMULATION_SETTINGS)
        settings.update(
            {
                "random_seed": seed,
                "grid_size": GRID_SIZE_BASE + 2,
                "n_agents": n_agents,
                "mapf_control": controller,
            }
        )
        settings["params_karma"]["karma_influence"] = karma_influence
        settings["params_karma"]["delta_threshold"] = delta_threshold
        metrics = run_single_simulation(settings)
        for name, value in metrics.items():
            if name not in metrics_lists:
                continue
            metrics_lists[name].append(value)

    aggregated: Dict[str, Tuple[float, float, float, float, float]] = {}
    for name, values in metrics_lists.items():
        aggregated[name] = summarize(values)
    return aggregated, metrics_lists


def _add_controller_label(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["controller_label"] = df.apply(
        lambda row: (
            f"{row['controller']} (delta={row['delta_threshold']})"
            if row["controller"] in KARMA_CONTROLLERS
            else f"{row['controller']} (baseline)"
        ),
        axis=1,
    )
    return df


def load_cached_results() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_path = OUTPUT_DIR / "summary.csv"
    raw_path = OUTPUT_DIR / "raw_values.csv"
    if not summary_path.exists() or not raw_path.exists():
        raise FileNotFoundError("Cached summary/raw files not found.")
    summary_df = pd.read_csv(summary_path)
    raw_df = pd.read_csv(raw_path)
    if RUNS_JSON.exists():
        run_df = pd.DataFrame(json.loads(RUNS_JSON.read_text()))
    else:
        run_df = pd.DataFrame()
    summary_df = _add_controller_label(summary_df)
    raw_df = _add_controller_label(raw_df)
    return summary_df, raw_df, run_df


def combine_seed_results() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    files = sorted(SEED_RESULTS_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError("No per-seed result files found.")

    raw_rows: List[Dict[str, Any]] = []
    for path in files:
        data = json.loads(path.read_text())
        for metric_name, value in data["metrics"].items():
            raw_rows.append(
                {
                    "controller": data["controller"],
                    "karma_influence": data["karma_influence"],
                    "delta_threshold": data["delta_threshold"],
                    "n_agents": data["n_agents"],
                    "metric": metric_name,
                    "value": value,
                    "seed": data["seed"],
                }
            )

    raw_df = pd.DataFrame(raw_rows)
    summary_rows: List[Dict[str, Any]] = []
    for (controller, influence, delta, n_agents, metric), group in raw_df.groupby(
        ["controller", "karma_influence", "delta_threshold", "n_agents", "metric"]
    ):
        stats = summarize(group["value"].tolist())
        summary_rows.append(
            {
                "controller": controller,
                "karma_influence": influence,
                "delta_threshold": delta,
                "n_agents": n_agents,
                "metric": metric,
                "mean": stats[0],
                "std": stats[1],
                "median": stats[2],
                "gini": stats[3],
                "iqr": stats[4],
                "n_runs": len(group),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df = _add_controller_label(summary_df)
    raw_df = _add_controller_label(raw_df)
    run_df = pd.DataFrame()
    return summary_df, raw_df, run_df


def collect_results() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    SEED_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not RECOMPUTE_RESULTS:
        try:
            return load_cached_results()
        except FileNotFoundError:
            try:
                return combine_seed_results()
            except FileNotFoundError:
                logger.info("No cache found, recomputing results.")

    # Recompute: clear old seed files
    for old_file in SEED_RESULTS_DIR.glob("*.json"):
        old_file.unlink()

    # Precompute total configs for progress logging
    total_configs = 0
    for controller in ALL_CONTROLLERS:
        if controller in KARMA_CONTROLLERS:
            total_configs += (
                len(KARMA_INFLUENCES) * len(DELTA_THRESHOLDS) * len(AGENT_COUNTS)
            )
        else:
            total_configs += len(AGENT_COUNTS)

    config_counter = 0
    pool_size = min(len(RANDOM_SEEDS), multiprocessing.cpu_count()) or 1
    print(f"Starting simulations with pool size {pool_size}...")
    with multiprocessing.Pool(processes=pool_size) as pool:
        for controller in ALL_CONTROLLERS:
            if controller in KARMA_CONTROLLERS:
                param_grid = [
                    (influence, delta)
                    for influence in KARMA_INFLUENCES
                    for delta in DELTA_THRESHOLDS
                ]
            else:
                param_grid = [
                    (
                        BASE_SIMULATION_SETTINGS["params_karma"]["karma_influence"],
                        BASE_SIMULATION_SETTINGS["params_karma"]["delta_threshold"],
                    )
                ]

            for n_agents in AGENT_COUNTS:
                for influence, delta in param_grid:
                    config_counter += 1
                    logger.info(
                        "[%d/%d] Config ctrl=%s agents=%d influence=%.2f delta=%.2f (seeds=%d, pool=%d)",
                        config_counter,
                        total_configs,
                        controller,
                        n_agents,
                        influence,
                        delta,
                        len(RANDOM_SEEDS),
                        pool_size,
                    )
                    jobs = [
                        (controller, influence, delta, n_agents, seed)
                        for seed in RANDOM_SEEDS
                    ]
                    seed_results = pool.map(_run_seed_job, jobs)
                    for res in seed_results:
                        _save_seed_result(res)

    summary_df, raw_df, run_df = combine_seed_results()

    summary_df.to_csv(OUTPUT_DIR / "summary.csv", index=False)
    raw_df.to_csv(OUTPUT_DIR / "raw_values.csv", index=False)
    summary_df.to_json(OUTPUT_DIR / "summary.json", orient="records", indent=2)
    RUNS_JSON.write_text(json.dumps([], indent=2))

    logger.info(
        "Finished all configurations. Summary rows: %d | Raw rows: %d",
        len(summary_df),
        len(raw_df),
    )
    return summary_df, raw_df, run_df


def _build_influence_plot_df(
    summary_df: pd.DataFrame, metric_name: str, n_agents: int
) -> pd.DataFrame:
    """Prepare data for influence plots, duplicating non-karma controllers as flat baselines."""
    baseline_influence = BASE_SIMULATION_SETTINGS["params_karma"]["karma_influence"]
    baseline_delta = BASE_SIMULATION_SETTINGS["params_karma"]["delta_threshold"]

    subsets: List[pd.DataFrame] = []

    # Karma controllers: keep their measured rows for this agent count
    karma_subset = summary_df.loc[
        (summary_df["metric"] == metric_name)
        & (summary_df["controller"].isin(KARMA_CONTROLLERS))
        & (summary_df["n_agents"] == n_agents)
    ].copy()
    karma_subset["controller_label"] = karma_subset.apply(
        lambda row: f"{row['controller']} (delta={row['delta_threshold']})", axis=1
    )
    subsets.append(karma_subset)

    # Non-karma controllers: duplicate their single measurement across all influence values
    non_karma = summary_df.loc[
        (summary_df["metric"] == metric_name)
        & (~summary_df["controller"].isin(KARMA_CONTROLLERS))
        & (summary_df["n_agents"] == n_agents)
    ]
    rows: List[pd.DataFrame] = []
    for influence in KARMA_INFLUENCES:
        dup = non_karma.copy()
        dup["karma_influence"] = influence
        dup["delta_threshold"] = baseline_delta
        dup["controller_label"] = dup.apply(
            lambda row: f"{row['controller']} (baseline)", axis=1
        )
        rows.append(dup)
    if rows:
        subsets.append(pd.concat(rows, ignore_index=True))

    return pd.concat(subsets, ignore_index=True) if subsets else pd.DataFrame()


def _build_controller_comparison_df(
    summary_df: pd.DataFrame,
    metric_name: str,
) -> pd.DataFrame:
    subset = summary_df.loc[summary_df["metric"] == metric_name].copy()
    subset["controller_label"] = subset.apply(
        lambda row: (
            f"{row['controller']} (inf={row['karma_influence']}, delta={row['delta_threshold']})"
            if row["controller"] in KARMA_CONTROLLERS
            else f"{row['controller']} (baseline)"
        ),
        axis=1,
    )
    return subset


def plot_line(metric_name: str, summary_df: pd.DataFrame, show_std: bool) -> None:
    for n_agents in AGENT_COUNTS:
        subset = _build_influence_plot_df(summary_df, metric_name, n_agents)
        if subset.empty:
            continue
        plt.style.use("seaborn-v0_8-paper")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.lineplot(
            data=subset,
            x="karma_influence",
            y="mean",
            hue="controller_label",
            style="controller_label",
            markers=True,
            dashes=False,
            estimator=None,
            ax=ax,
        )

        if show_std and "std" in subset.columns:
            for label, grp in subset.groupby("controller_label"):
                grp_sorted = grp.sort_values("karma_influence")
                color = None
                for line in ax.get_lines():
                    if line.get_label() == label:
                        color = line.get_color()
                        break
                ax.fill_between(
                    grp_sorted["karma_influence"],
                    grp_sorted["mean"] - grp_sorted["std"],
                    grp_sorted["mean"] + grp_sorted["std"],
                    color=color,
                    alpha=0.15,
                )

        plt.xlabel("Karma Influence")
        plt.ylabel(metric_name)
        plt.title(
            f"{metric_name} vs Karma Influence (agents={n_agents}, grid={GRID_SIZE_BASE})"
        )
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        suffix = "std" if show_std else "nostd"
        fname = f"line_{metric_name.replace(' ', '_').replace('%', 'perc')}_{n_agents}_grid{GRID_SIZE_BASE}_{suffix}.pdf"
        plt.savefig(FIGS_DIR / fname, dpi=300)
        plt.close(fig)
        logger.info(
            "Saved combined line plot %s for %s (agents=%d, std=%s)",
            fname,
            metric_name,
            n_agents,
            show_std,
        )


def plot_controller_comparison(summary_df: pd.DataFrame, show_std: bool) -> None:
    """Compare controllers across agents with all karma parameter combinations in one figure per metric."""

    for metric in CONTROLLER_COMPARISON_METRICS:
        subset = _build_controller_comparison_df(summary_df, metric)
        if subset.empty:
            continue

        plt.style.use("seaborn-v0_8-paper")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.lineplot(
            data=subset,
            x="n_agents",
            y="mean",
            hue="controller_label",
            style="controller_label",
            markers=True,
            dashes=False,
            estimator=None,
            ax=ax,
        )

        if show_std and "std" in subset.columns:
            for label, grp in subset.groupby("controller_label"):
                grp_sorted = grp.sort_values("n_agents")
                color = None
                for line in ax.get_lines():
                    if line.get_label() == label:
                        color = line.get_color()
                        break
                ax.fill_between(
                    grp_sorted["n_agents"],
                    grp_sorted["mean"] - grp_sorted["std"],
                    grp_sorted["mean"] + grp_sorted["std"],
                    color=color,
                    alpha=0.15,
                )

        plt.xlabel("Number of Agents")
        plt.ylabel(metric)
        plt.title(f"Controller comparison (all karma params, grid={GRID_SIZE_BASE})")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        metric_token = metric.replace(" ", "_").replace("%", "perc")
        suffix = "std" if show_std else "nostd"
        fname = (
            f"controller_comparison_{metric_token}_grid{GRID_SIZE_BASE}_{suffix}.pdf"
        )
        plt.savefig(FIGS_DIR / fname, dpi=300)
        plt.close(fig)
        logger.info(
            "Saved controller comparison plot %s for %s (std=%s)",
            fname,
            metric,
            show_std,
        )


def plot_heatmaps(metric_name: str, summary_df: pd.DataFrame) -> None:
    # Heatmaps removed per request to keep all controllers in shared line plots
    return


def plot_box(metric_name: str, raw_df: pd.DataFrame) -> None:
    # Skip box plots to keep figure count minimal
    return


def main():
    summary_df, raw_df, _run_df = collect_results()

    for metric in LINE_METRICS:
        plot_line(metric, summary_df, show_std=False)
        plot_line(metric, summary_df, show_std=True)
        plot_heatmaps(metric, summary_df)

    # Benchmark: compare karma controllers against other decentralized controllers
    plot_controller_comparison(summary_df, show_std=False)
    plot_controller_comparison(summary_df, show_std=True)

    logger.info("Saved aggregated results and plots to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
