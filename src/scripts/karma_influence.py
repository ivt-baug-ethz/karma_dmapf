"""Single-grid karma influence analysis.

This script mirrors the core mechanics of ``karma_influence_sweep.py`` but
targets one grid size and one agent count. It sweeps only the karma influence
parameter (delta is fixed to 0) for four controllers: token-passing, egoistic,
utilitarian, and karma. Seeded runs are parallelized. Results are written
to a timestamped folder under ``results/runs/`` and aggregated into a single
``summary.json`` stored both in that folder and in ``results/karma_influence/``
for downstream plotting (``figures/Figure_3.py``).
"""

from __future__ import annotations

import copy
import json
import logging
import multiprocessing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
from tqdm import tqdm

from src.simulation.constants import (
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
)
from src.simulation.environment import Environment
from src.planners.astar import AStarPathPlanner

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# Global knobs (edit here for reproducibility)
GRID_SIZE = 5  # base grid size (without +2 padding) - values: 5, 10, 15
N_AGENTS = 10  # values: 10, 30, 80
DELTA_THRESHOLD = 0
INFLUENCES = [round(x * 0.1, 1) for x in range(0, 11)]
SEEDS = list(range(41, 61))
TIME_SIMULATION_DURATION = 100
SUMMARY_FILENAME = (
    f"summary_grid{GRID_SIZE}_agents{N_AGENTS}_T{TIME_SIMULATION_DURATION}.json"
)


@dataclass(frozen=True)
class ExperimentConfig:
    grid_size: int
    n_agents: int
    influences: List[float]
    seeds: List[int]
    time_simulation_duration: int
    time_horizon_visualization: int
    delta_threshold: float = DELTA_THRESHOLD


BASE_SIMULATION_SETTINGS: Dict[str, Any] = {
    "time_horizon_visualization": TIME_SIMULATION_DURATION,
    "time_simulation_duration": TIME_SIMULATION_DURATION,
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
        "delta_threshold": DELTA_THRESHOLD,
        "karma_influence": 0.5,
    },
    "debug_statements": False,
}

CONTROLLERS = [
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
]


# --- Local analysis helpers ---
def gini(x: Iterable[float]) -> float:
    arr = np.array(list(x), dtype=float)
    if len(arr) == 0:
        return 0.0
    mad = np.abs(np.subtract.outer(arr, arr)).mean()
    return 0.5 * mad / np.mean(arr)


def summarize(x: Iterable[float]) -> Tuple[float, float, float, float, float]:
    arr = np.array(list(x), dtype=float)
    if len(arr) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    return (
        arr.mean(),
        arr.std(ddof=0),
        np.median(arr),
        gini(arr),
        np.percentile(arr, 75) - np.percentile(arr, 25),
    )


def compute_run_metrics(
    completed_tasks_by_agent: Dict[int, List[Any]],
    n_astar_calls: float,
) -> Dict[str, float]:
    """Compute only the metric needed for plotting: avg service time increase over all tasks."""

    all_completed_tasks = [
        task for task_list in completed_tasks_by_agent.values() for task in task_list
    ]

    task_service_times = [
        task.completed_time - task.pickup_time
        for task in all_completed_tasks
        if task.completed_time is not None and task.pickup_time is not None
    ]
    task_min_times = [
        task.minimum_task_time
        for task in all_completed_tasks
        if task.minimum_task_time != 0
    ]

    if len(task_service_times) != len(task_min_times):
        raise ValueError("Completed task counts do not align; cannot summarize.")

    service_increase_pct = [
        (s_time - m_time) / m_time * 100
        for s_time, m_time in zip(task_service_times, task_min_times)
    ]

    return {
        "Avg Service Time Increase (%) (all agents)": float(
            np.mean(service_increase_pct) if service_increase_pct else 0.0
        ),
    }


def _sanitize_float(value: float) -> str:
    return str(value).replace(".", "p")


def _build_settings(base: Dict[str, Any], cfg: ExperimentConfig) -> Dict[str, Any]:
    settings = copy.deepcopy(base)
    settings["time_simulation_duration"] = cfg.time_simulation_duration
    settings["time_horizon_visualization"] = cfg.time_horizon_visualization
    settings["params_karma"]["delta_threshold"] = cfg.delta_threshold
    return settings


def _seed_result_path(out_dir: Path, result: Dict[str, Any]) -> Path:
    fname = (
        f"seed{result['seed']}_ctrl{result['controller']}"
        f"_inf{_sanitize_float(result['karma_influence'])}"
        f"_delta{_sanitize_float(result['delta_threshold'])}"
        f"_agents{result['n_agents']}.json"
    )
    return out_dir / fname


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
        leave=False,
    ):
        env.step()
        n_astar_calls += AStarPathPlanner.get_counter()
        AStarPathPlanner.reset_counter()

    return compute_run_metrics(env.completed_tasks, n_astar_calls)


def _run_seed_job(
    args: Tuple[str, float, int, int, Dict[str, Any], int],
) -> Dict[str, Any]:
    controller, karma_influence, n_agents, seed, base_settings, grid_size = args
    settings = copy.deepcopy(base_settings)
    settings.update(
        {
            "random_seed": seed,
            "grid_size": grid_size,
            "n_agents": n_agents,
            "mapf_control": controller,
        }
    )
    settings["params_karma"]["karma_influence"] = karma_influence
    start_ts = perf_counter()
    metrics = run_single_simulation(settings)
    duration_sec = perf_counter() - start_ts
    logger.info(
        "Seed run | ctrl=%s agents=%d influence=%.2f delta=%.2f seed=%d duration=%.2fs",
        controller,
        n_agents,
        karma_influence,
        settings["params_karma"]["delta_threshold"],
        seed,
        duration_sec,
    )
    return {
        "controller": controller,
        "karma_influence": karma_influence,
        "delta_threshold": settings["params_karma"]["delta_threshold"],
        "n_agents": n_agents,
        "grid_size": grid_size,
        "seed": seed,
        "metrics": metrics,
        "duration_seconds": duration_sec,
    }


def _save_seed_result(out_dir: Path, result: Dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _seed_result_path(out_dir, result).write_text(json.dumps(result, indent=2))


def _combine_seed_results(
    out_dir: Path,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    files = sorted(out_dir.glob("seed*.json"))
    if not files:
        raise FileNotFoundError("No per-seed result files found; nothing to combine.")

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
                    "grid_size": data["grid_size"],
                    "metric": metric_name,
                    "value": value,
                    "seed": data["seed"],
                }
            )

    summary_rows: List[Dict[str, Any]] = []
    key_fn = lambda r: (
        r["controller"],
        r["karma_influence"],
        r["delta_threshold"],
        r["n_agents"],
        r["grid_size"],
        r["metric"],
    )
    grouped: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
    for row in raw_rows:
        grouped.setdefault(key_fn(row), []).append(row)

    for key, rows in grouped.items():
        values = [r["value"] for r in rows]
        mean, std, median, gini, iqr = summarize(values)
        controller, influence, delta, n_agents, grid_size, metric = key
        summary_rows.append(
            {
                "controller": controller,
                "karma_influence": influence,
                "delta_threshold": delta,
                "n_agents": n_agents,
                "grid_size": grid_size,
                "metric": metric,
                "mean": mean,
                "std": std,
                "median": median,
                "gini": gini,
                "iqr": iqr,
                "n_runs": len(values),
            }
        )

    return summary_rows, raw_rows


def _write_summary(
    out_dir: Path,
    logs_dir: Path,
    metadata: Dict[str, Any],
    summary_rows: List[Dict[str, Any]],
    raw_rows: List[Dict[str, Any]],
) -> Path:
    payload = {
        "metadata": metadata,
        "summary": summary_rows,
        "raw": raw_rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / SUMMARY_FILENAME
    summary_path.write_text(json.dumps(payload, indent=2))
    (logs_dir / SUMMARY_FILENAME).write_text(json.dumps(payload, indent=2))
    return summary_path


def main() -> None:
    cfg = ExperimentConfig(
        grid_size=GRID_SIZE,
        n_agents=N_AGENTS,
        influences=INFLUENCES,
        seeds=SEEDS,
        time_simulation_duration=TIME_SIMULATION_DURATION,
        time_horizon_visualization=TIME_SIMULATION_DURATION,
        delta_threshold=DELTA_THRESHOLD,
    )

    results_root = Path(__file__).resolve().parents[2] / "results"
    logs_dir = results_root / "karma_influence"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = results_root / "runs" / f"karma_influence_{timestamp}"

    base_settings = _build_settings(BASE_SIMULATION_SETTINGS, cfg)
    env_grid_size = cfg.grid_size + 2  # preserve existing +2 padding convention

    logger.info(
        "Starting karma influence sweep | grid=%dx%d (env=%d) agents=%d influences=%s seeds=%d dir=%s",
        cfg.grid_size,
        cfg.grid_size,
        env_grid_size,
        cfg.n_agents,
        cfg.influences,
        len(cfg.seeds),
        out_dir.name,
    )

    pool_size = min(len(cfg.seeds), multiprocessing.cpu_count()) or 1
    jobs: List[Tuple[str, float, int, int, Dict[str, Any], int]] = []
    for controller in CONTROLLERS:
        for influence in cfg.influences:
            for seed in cfg.seeds:
                jobs.append(
                    (
                        controller,
                        influence,
                        cfg.n_agents,
                        seed,
                        base_settings,
                        env_grid_size,
                    )
                )

    logger.info(
        "Dispatching %d seed runs (pool=%d) across %d controllers and %d influences",
        len(jobs),
        pool_size,
        len(CONTROLLERS),
        len(cfg.influences),
    )

    with multiprocessing.Pool(processes=pool_size) as pool:
        for result in tqdm(
            pool.imap_unordered(_run_seed_job, jobs),
            total=len(jobs),
            desc="Seed runs",
            leave=True,
        ):
            _save_seed_result(out_dir, result)

    summary_rows, raw_rows = _combine_seed_results(out_dir)

    metadata = {
        "timestamp_dir": out_dir.name,
        "grid_size_base": cfg.grid_size,
        "grid_size_env": env_grid_size,
        "n_agents": cfg.n_agents,
        "delta_threshold": cfg.delta_threshold,
        "influences": cfg.influences,
        "seeds": cfg.seeds,
        "controllers": CONTROLLERS,
        "time_simulation_duration": cfg.time_simulation_duration,
        "time_horizon_visualization": cfg.time_horizon_visualization,
        "summary_filename": SUMMARY_FILENAME,
    }

    summary_path = _write_summary(out_dir, logs_dir, metadata, summary_rows, raw_rows)
    logger.info("Saved summary to %s and copied to %s", summary_path, logs_dir)


if __name__ == "__main__":
    main()
