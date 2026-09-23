from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.simulation.agent import Agent
    from src.simulation.task import Task
    from numpy.typing import NDArray

import numpy as np
from scipy.optimize import linear_sum_assignment
from src.simulation.geometry import Geometry
from src.simulation.constants import AGENT_STATUS_CARRY


class Planner_Assignment_Central:
    @staticmethod
    def estimate_agent_availability(
        agent: "Agent", current_time: int
    ) -> Tuple[List[int], int, int]:
        """
        Returns:
            (available_position, available_time, orientation)
        """
        # Case 1: idle agent
        if agent.is_idle():
            return agent.current_position, current_time, agent.current_orientation

        # Case 2: busy agent → assume it will finish current task (CARRYING STATUS)
        elif agent.status == AGENT_STATUS_CARRY:
            remaining_steps: int = len(agent.route)

            # fallback: if no route exists yet, assume 0
            if remaining_steps is None:
                return agent.current_position, current_time, agent.current_orientation

            available_time: int = current_time + remaining_steps

            # if agent is in carry state, it should have an assigned task
            if agent.assigned_task is None:
                raise ValueError(
                    f"Agent {agent.id} is in CARRY status but has no assigned task."
                )

            # after finishing, agent will be at delivery location
            available_position: List[int] = agent.assigned_task.to_position
            # orientation approximation (keep current)
            orientation: int = agent.current_orientation
            return available_position, available_time, orientation

        raise ValueError(
            f"Agent {agent.id} has unsupported status {agent.status} for availability estimation."
        )

    @staticmethod
    def plan_assignment(
        candidate_agents: List["Agent"],
        open_tasks: List["Task"],
        time: int,
        alpha: float = 0.2,
    ) -> Tuple[NDArray[np.int_], NDArray[np.int_]]:
        """
        Compute optimal agent-task assignment using Hungarian algorithm.
        The assignment costs include travel time (manhattan distance + rotation)
        but also the time since a task was not assigned yet.
        This tradeoff is balanced using a factor alpha.
        Agents that are in status IDLE or CARRY will be considered for assignment.

        all_agents: list of agents
        open_tasks: list of tasks
        time: current time
        alpha: weight for task's wait time in cost function
        """
        num_agents: int = len(candidate_agents)
        num_tasks: int = len(open_tasks)
        if num_agents == 0 or num_tasks == 0:
            return np.array([]), np.array([])

        cost_matrix: NDArray[np.float64] = np.zeros((num_agents, num_tasks))
        for i, agent in enumerate(candidate_agents):
            start_pos, start_time, orientation = (
                Planner_Assignment_Central.estimate_agent_availability(agent, time)
            )
            for j, task in enumerate(open_tasks):
                # travel from availability position to pickup
                travel_time = Geometry.travel_time_with_rotation(
                    (start_pos[0], start_pos[1]),
                    (task.from_position[0], task.from_position[1]),
                    orientation,
                )
                arrival_time: int = start_time + travel_time
                wait_time: int = arrival_time - task.spawned_time
                cost_matrix[i, j] = arrival_time - alpha * wait_time
        # Hungarian algorithm
        agent_indices, task_indices = linear_sum_assignment(cost_matrix)
        return agent_indices, task_indices
