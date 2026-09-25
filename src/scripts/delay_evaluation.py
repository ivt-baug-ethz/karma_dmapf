"""Task time, task delay and cumulative agent delay per controller.

Runs token-passing, egoistic, utilitarian and karma (no reset, at several karma
influences) on the 5x5/10 and 10x10/30 scenarios. Seeded runs are parallelized.
Per-seed results are written to a timestamped folder under ``results/runs/``, and
one ``tasks_grid{G}_agents{N}_T{T}.json`` per scenario (summary rows, metrics,
negotiation case counts and the per-task records of every run) is written to
``results/delay_evaluation/`` for downstream plotting (``figures/Figure_5.py``).
"""

from __future__ import annotations

import copy
import json
import logging
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from tqdm import tqdm

from src.simulation.metrics import compute_run_metrics, summarize
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
SCENARIOS = [(5, 10), (10, 30)]  # (base grid size without +2 padding, agents)
DELTA_THRESHOLD = 0
INFLUENCES = [0.1, 0.25, 0.5, 0.75, 0.9]
SEEDS = list(range(41, 51))
TIME_SIMULATION_DURATION = 300


@dataclass(frozen=True)
class ExperimentConfig:
    scenarios: List[Tuple[int, int]]
    influences: List[float]
    seeds: List[int]
    time_simulation_duration: int
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

PRINTED_METRICS = [
    "Completed Tasks",
    "Avg Task Time (incl. Reallocation) (all agents)",
    "Avg Task Delay (all agents)",
    "Avg Service Time (all agents)",
    "Std Cumulative Delay (per agent)",
]


def _summary_filename(grid_size: int, n_agents: int) -> str:
    return f"tasks_grid{grid_size}_agents{n_agents}_T{TIME_SIMULATION_DURATION}.json"


def run_single_simulation(
    simulation_settings: Dict[str, Any],
) -> Tuple[Dict[str, float], Dict[str, int], List[List[int]]]:
    AStarPathPlanner.reset_counter()
    env = Environment(settings=simulation_settings)

    for _ in range(2 * simulation_settings["n_agents"]):
        env.spawn_agent()

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

    # one record per completed task, the columns are named in the metadata
    tasks = [
        [
            agent_id,
            task.assigned_time,
            task.pickup_time,
            task.completed_time,
            task.minimum_pickup_time,
            task.minimum_task_time,
        ]
        for agent_id, agent_tasks in env.completed_tasks.items()
        for task in agent_tasks
    ]

    return (
        compute_run_metrics(env.completed_tasks, n_astar_calls),
        dict(env.negotiation_cases),
        tasks,
    )


def _run_seed_job(
    args: Tuple[str, Optional[float], int, int, int, Dict[str, Any]],
) -> Dict[str, Any]:
    controller, karma_influence, grid_size, n_agents, seed, base_settings = args
    settings = copy.deepcopy(base_settings)
    settings.update(
        {
            "random_seed": seed,
            "grid_size": grid_size + 2,
            "n_agents": n_agents,
            "mapf_control": controller,
        }
    )

    if karma_influence is not None:
        settings["params_karma"]["karma_influence"] = karma_influence

    start_ts = perf_counter()
    metrics, negotiation_cases, tasks = run_single_simulation(settings)
    duration_sec = perf_counter() - start_ts
    logger.info(
        "Seed run | ctrl=%s grid=%d agents=%d influence=%s seed=%d duration=%.2fs",
        controller,
        grid_size,
        n_agents,
        karma_influence,
        seed,
        duration_sec,
    )

    return {
        "controller": controller,
        "karma_influence": karma_influence,
        "grid_size": grid_size,
        "n_agents": n_agents,
        "seed": seed,
        "metrics": metrics,
        "negotiation_cases": negotiation_cases,
        "tasks": tasks,
        "duration_seconds": duration_sec,
    }


def _save_seed_result(out_dir: Path, result: Dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = (
        f"seed{result['seed']}_ctrl{result['controller']}"
        f"_inf{str(result['karma_influence']).replace('.', 'p')}"
        f"_grid{result['grid_size']}_agents{result['n_agents']}.json"
    )
    (out_dir / fname).write_text(json.dumps(result))


def _summarize_runs(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[Any, ...], List[float]] = {}
    for run in runs:
        for metric_name, value in run["metrics"].items():
            key = (run["controller"], run["karma_influence"], metric_name)
            grouped.setdefault(key, []).append(value)

    summary_rows: List[Dict[str, Any]] = []
    for (controller, influence, metric), values in grouped.items():
        mean, std, median, gini, iqr = summarize(values)
        summary_rows.append(
            {
                "controller": controller,
                "karma_influence": influence,
                "metric": metric,
                "mean": mean,
                "std": std,
                "median": median,
                "gini": gini,
                "iqr": iqr,
                "n_runs": len(values),
            }
        )

    return summary_rows


def _print_scenario(grid_size: int, n_agents: int, runs: List[Dict[str, Any]]) -> None:
    print(f"\n=== {grid_size}x{grid_size} grid, {n_agents} agents ===")
    series = sorted(
        {(r["controller"], r["karma_influence"]) for r in runs},
        key=lambda s: (CONTROLLERS.index(s[0]), s[1] or 0.0),
    )

    for controller, influence in series:
        series_runs = [
            r
            for r in runs
            if r["controller"] == controller and r["karma_influence"] == influence
        ]
        label = controller if influence is None else f"{controller} tau={influence}"
        print(f"\n{label}")

        for metric in PRINTED_METRICS:
            values = [r["metrics"][metric] for r in series_runs]
            print(f"  {metric:<36} {np.mean(values):8.2f} +- {np.std(values):6.2f}")
        cases: Counter[str] = Counter()

        for r in series_runs:
            cases.update(r["negotiation_cases"])

        for case, count in sorted(cases.items()):
            print(f"  {case:<70} {count:6d}")


def main() -> None:
    cfg = ExperimentConfig(
        scenarios=SCENARIOS,
        influences=INFLUENCES,
        seeds=SEEDS,
        time_simulation_duration=TIME_SIMULATION_DURATION,
        delta_threshold=DELTA_THRESHOLD,
    )

    results_root = Path(__file__).resolve().parents[2] / "results"
    logs_dir = results_root / "delay_evaluation"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = results_root / "runs" / f"delay_evaluation_{timestamp}"

    base_settings = copy.deepcopy(BASE_SIMULATION_SETTINGS)
    base_settings["params_karma"]["delta_threshold"] = cfg.delta_threshold

    # the karma influence only matters for karma, so the other controllers run once
    jobs: List[Tuple[str, Optional[float], int, int, int, Dict[str, Any]]] = []
    for grid_size, n_agents in cfg.scenarios:
        for controller in CONTROLLERS:
            influences: List[Optional[float]] = (
                list(cfg.influences)
                if controller == MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA
                else [None]
            )

            for influence in influences:
                for seed in cfg.seeds:
                    jobs.append(
                        (
                            controller,
                            influence,
                            grid_size,
                            n_agents,
                            seed,
                            base_settings,
                        )
                    )

    max_workers = min(len(jobs), os.cpu_count() or 1)
    logger.info(
        "Dispatching %d seed runs (workers=%d) across %d scenarios, dir=%s",
        len(jobs),
        max_workers,
        len(cfg.scenarios),
        out_dir.name,
    )

    runs: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for result in tqdm(
            executor.map(_run_seed_job, jobs),
            total=len(jobs),
            desc="Seed runs",
            leave=True,
        ):
            _save_seed_result(out_dir, result)
            runs.append(result)

    logs_dir.mkdir(parents=True, exist_ok=True)
    for grid_size, n_agents in cfg.scenarios:
        scenario_runs = [
            {k: v for k, v in r.items() if k not in ("grid_size", "n_agents")}
            for r in runs
            if r["grid_size"] == grid_size and r["n_agents"] == n_agents
        ]
        payload = {
            "metadata": {
                "timestamp_dir": out_dir.name,
                "grid_size_base": grid_size,
                "grid_size_env": grid_size + 2,
                "n_agents": n_agents,
                "delta_threshold": cfg.delta_threshold,
                "influences": cfg.influences,
                "seeds": cfg.seeds,
                "controllers": CONTROLLERS,
                "time_simulation_duration": cfg.time_simulation_duration,
                "task_columns": [
                    "agent_id",
                    "assigned_time",
                    "pickup_time",
                    "completed_time",
                    "minimum_pickup_time",
                    "minimum_task_time",
                ],
            },
            "summary": _summarize_runs(scenario_runs),
            "runs": scenario_runs,
        }
        summary_path = logs_dir / _summary_filename(grid_size, n_agents)
        summary_path.write_text(json.dumps(payload))
        logger.info("Saved %s", summary_path)
        _print_scenario(grid_size, n_agents, scenario_runs)


if __name__ == "__main__":
    main()
