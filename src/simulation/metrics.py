"""Shared analysis utilities for MAPF evaluations.

Functions here intentionally mirror the implementations used in
scripts/karma_influence.py so that downstream scripts can re-use logic without
altering behavior.
"""

from __future__ import annotations

from typing import Iterable, Tuple, Dict, Any, List
import numpy as np


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
    """Compute per-run metrics shared by analysis scripts.

    The logic mirrors the calculations in scripts/karma_influence.py to keep results
    consistent across evaluation scripts.
    """

    all_completed_tasks = [
        task for task_list in completed_tasks_by_agent.values() for task in task_list
    ]

    # task time runs from the assignment to the drop-off, the task delay subtracts the
    # unobstructed time from the agent's pose at assignment via the pickup to the drop-off
    task_total_times = [
        task.completed_time - task.assigned_time
        for task in all_completed_tasks
        if task.completed_time is not None
    ]
    task_delays = [
        task.completed_time
        - task.assigned_time
        - task.minimum_pickup_time
        - task.minimum_task_time
        for task in all_completed_tasks
        if task.completed_time is not None
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

    task_service_increase_percentages: List[float] = []
    for s_time, m_time in zip(task_service_times, task_min_times):
        task_service_increase_percentages.append((s_time - m_time) / m_time * 100)

    if len(task_total_times) != len(task_service_times) or len(task_total_times) != len(
        task_service_increase_percentages
    ):
        raise ValueError(
            "Completed task counts do not align across metrics; cannot summarize."
        )

    list_agent_avg_service_times: List[float] = []
    list_agent_avg_service_increases: List[float] = []
    for agent_tasks in completed_tasks_by_agent.values():
        a_service_times = [
            task.completed_time - task.pickup_time
            for task in agent_tasks
            if task.completed_time is not None and task.pickup_time is not None
        ]
        a_min_times = [
            task.minimum_task_time
            for task in agent_tasks
            if task.minimum_task_time != 0
        ]
        a_increases: List[float] = []
        for s_time, m_time in zip(a_service_times, a_min_times):
            a_increases.append((s_time - m_time) / m_time * 100)
        if len(a_service_times) > 0:
            list_agent_avg_service_times.append(float(np.mean(a_service_times)))
        if len(a_increases) > 0:
            list_agent_avg_service_increases.append(float(np.mean(a_increases)))

    list_agent_cumulative_delays: List[float] = [
        float(
            sum(
                task.completed_time
                - task.assigned_time
                - task.minimum_pickup_time
                - task.minimum_task_time
                for task in agent_tasks
                if task.completed_time is not None
            )
        )
        for agent_tasks in completed_tasks_by_agent.values()
    ]

    n_avg_service_time_per_agent = (
        float(np.mean(list_agent_avg_service_times))
        if list_agent_avg_service_times
        else 0.0
    )
    n_avg_service_increase_per_agent = (
        float(np.mean(list_agent_avg_service_increases))
        if list_agent_avg_service_increases
        else 0.0
    )

    return {
        "A* Calls": float(n_astar_calls),
        "Completed Tasks": float(len(task_total_times)),
        "Total Task Time (incl. Reallocation) (all agents)": float(
            np.sum(task_total_times)
        ),
        "Avg Task Time (incl. Reallocation) (all agents)": float(
            np.mean(task_total_times)
        ),
        "Std Task Time (incl. Reallocation) (all agents)": float(
            np.std(task_total_times)
        ),
        "Avg Task Delay (all agents)": float(np.mean(task_delays)),
        "Std Task Delay (all agents)": float(np.std(task_delays)),
        "Total Service Time (all agents)": float(np.sum(task_service_times)),
        "Avg Service Time (all agents)": float(np.mean(task_service_times)),
        "Std Service Time (all agents)": float(np.std(task_service_times)),
        "Avg Service Time Increase (%) (all agents)": float(
            np.mean(task_service_increase_percentages)
        ),
        "Avg Service Time (per agent mean)": float(n_avg_service_time_per_agent),
        "Avg Service Increase (%) (per agent mean)": float(
            n_avg_service_increase_per_agent
        ),
        "Avg Cumulative Delay (per agent)": float(
            np.mean(list_agent_cumulative_delays)
        ),
        "Std Cumulative Delay (per agent)": float(np.std(list_agent_cumulative_delays)),
        "Gini Cumulative Delay (per agent)": float(gini(list_agent_cumulative_delays)),
    }
