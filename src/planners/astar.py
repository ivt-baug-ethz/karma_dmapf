"""A STAR BASED PATH PLANNER"""

from __future__ import annotations
from typing import List, Optional, Tuple, Set, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
    from src.simulation.agent import Agent

import heapq
import threading
from src.simulation.constants import DIRS, DIR_NAMES


class PathPlannerState:
    def __init__(
        self,
        x: int,
        y: int,
        theta: int,
        t: int,
        action: Optional[str],
        goal_reached: bool = False,
    ):
        self.x: int = x
        self.y: int = y
        self.theta: int = theta
        self.t: int = t
        self.action: Optional[str] = action
        self.goal_reached: bool = goal_reached

    def __lt__(self, other: "PathPlannerState") -> bool:
        return self.t < other.t

    def __repr__(self) -> str:
        return (
            f"PathPlannerState(x={self.x}, y={self.y}, theta={self.theta}, "
            f"t={self.t}, action={self.action}, goal_reached={self.goal_reached})"
        )


"""
The planner is not just “shortest path to goal” in space and time.
It is “shortest path that reaches the goal at least once and then finishes in a safe resting state.”

This is important to make sure that after reaching goal, no conflicts happen during parking position!
"""


class AStarPathPlanner:
    COUNTER: int = 0
    _thread_local = threading.local()

    def __init__(
        self, static_occupancy_grid: NDArray[np.int_], astar_params: Dict[str, Any]
    ):
        self.static_occupancy_grid: NDArray[np.int_] = static_occupancy_grid
        self.astar_params: Dict[str, Any] = astar_params

    @classmethod
    def increment_counter(cls) -> None:
        current_count = getattr(cls._thread_local, "counter", 0)
        cls._thread_local.counter = current_count + 1

    @classmethod
    def get_counter(cls) -> int:
        return getattr(cls._thread_local, "counter", 0)

    @classmethod
    def reset_counter(cls) -> None:
        cls._thread_local.counter = 0

    def manhattan(self, a: Tuple[int, int], b: Tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def heuristic(
        self, a: Tuple[int, int], goal: Tuple[int, int], goal_reached: bool
    ) -> int:
        # once the goal was reached, only a free resting cell is searched, at unknown distance
        return 0 if goal_reached else self.manhattan(a, goal)

    def goal_remains_free(
        self,
        goal_state: PathPlannerState,
        reservation_grid: Optional[NDArray[np.int_]],
        planning_horizon: int,
    ) -> bool:
        if reservation_grid is None:
            return True

        latest_known_time = min(
            planning_horizon,
            reservation_grid.shape[0] - 1,
        )
        for t in range(goal_state.t, latest_known_time + 1):
            if reservation_grid[t, goal_state.x, goal_state.y] != -1:
                return False
        return True

    def astar(
        self,
        start: Tuple[int, int, int],
        goal: Tuple[int, int],
        reservation_grid: Optional[NDArray[np.int_]] = None,
        ignore_counter: bool = False,
        planning_horizon: Optional[int] = None,
    ) -> Optional[List[PathPlannerState]]:
        """
        This is the implementation of a astar algorithm for a robot that needs
        to rotate into the direction of travel, and can wait.
        It considers obstables from a static_occupancy map and a reservation grid.

        start: (x, y, theta)
        goal: (x, y)
        reservation_grid: 3D reservation grid [time, x, y] storing agent ids (-1 means free)
        max_time_horizon: optional maximum time to consider
        ignore_counter: if True, do not increment the AStarPathPlanner.COUNTER (used for shortest possible path calculation for evaluation only)
        """
        effective_planning_horizon = (
            self.astar_params["planning_horizon"]
            if planning_horizon is None
            else planning_horizon
        )
        reservation_horizon: Optional[int] = None
        if reservation_grid is not None:
            if reservation_grid.shape[0] == 0:
                return None
            reservation_horizon = reservation_grid.shape[0] - 1
            effective_planning_horizon = min(
                effective_planning_horizon, reservation_horizon
            )
        open_list: List[Tuple[int, PathPlannerState, List[PathPlannerState]]] = []
        visited: Set[Tuple[int, int, int, int, bool]] = set()
        steps: int = 0
        start_state: PathPlannerState = PathPlannerState(
            start[0], start[1], start[2], 0, "start", (start[0], start[1]) == goal
        )
        heapq.heappush(
            open_list,
            (self.manhattan((start[0], start[1]), goal), start_state, []),
        )
        if not ignore_counter:
            AStarPathPlanner.increment_counter()

        while open_list:
            steps += 1
            # ABORT CONDITION: TIMEOUT
            if steps > self.astar_params["max_iterations"]:
                # print("\t\tASTAR [TIMEOUT] A* aborted")
                return None
            # EXPLORE NEW STEP
            f, state, path = heapq.heappop(open_list)
            key: Tuple[int, int, int, int, bool] = (
                state.x,
                state.y,
                state.theta,
                state.t,
                state.goal_reached,
            )
            if key in visited:
                continue
            visited.add(key)
            new_path: List[PathPlannerState] = path + [state]

            if reservation_grid is not None:
                if (
                    state.t < reservation_grid.shape[0]
                    and reservation_grid[state.t, state.x, state.y] != -1
                ):
                    continue

            # ABORT CONDITION: FOUND GOAL
            if state.goal_reached and self.goal_remains_free(
                state, reservation_grid, effective_planning_horizon
            ):
                return new_path

            # EXPLORE
            next_t: int = state.t + 1
            if next_t > effective_planning_horizon:
                continue

            # BRANCH 1: ACTION: WAIT
            if reservation_grid is None or (
                next_t < reservation_grid.shape[0]
                and reservation_grid[next_t, state.x, state.y] == -1
            ):
                heapq.heappush(
                    open_list,
                    (
                        next_t
                        + self.heuristic((state.x, state.y), goal, state.goal_reached),
                        PathPlannerState(
                            state.x,
                            state.y,
                            state.theta,
                            next_t,
                            "T",
                            state.goal_reached or (state.x, state.y) == goal,
                        ),
                        new_path,
                    ),
                )

            # BRANCH 2: ACTION: ROTATE (turn left/right)
            if reservation_grid is None or (
                next_t < reservation_grid.shape[0]
                and reservation_grid[next_t, state.x, state.y] == -1
            ):
                heapq.heappush(
                    open_list,
                    (
                        next_t
                        + self.heuristic((state.x, state.y), goal, state.goal_reached),
                        PathPlannerState(
                            state.x,
                            state.y,
                            (state.theta - 1) % 4,
                            next_t,
                            "A",
                            state.goal_reached or (state.x, state.y) == goal,
                        ),
                        new_path,
                    ),
                )
                heapq.heappush(
                    open_list,
                    (
                        next_t
                        + self.heuristic((state.x, state.y), goal, state.goal_reached),
                        PathPlannerState(
                            state.x,
                            state.y,
                            (state.theta + 1) % 4,
                            next_t,
                            "C",
                            state.goal_reached or (state.x, state.y) == goal,
                        ),
                        new_path,
                    ),
                )

            # BRANCH 3: ACTION: MOVE FORWARD
            dx, dy = DIRS[state.theta]
            nx, ny = state.x + dx, state.y + dy
            if (
                0 <= nx < self.static_occupancy_grid.shape[0]
                and 0 <= ny < self.static_occupancy_grid.shape[1]
            ):
                if self.static_occupancy_grid[nx, ny] == 0:
                    if reservation_grid is None or (
                        next_t < reservation_grid.shape[0]
                        and reservation_grid[next_t, nx, ny] == -1
                        and not (
                            state.t < reservation_grid.shape[0]
                            and reservation_grid[state.t, nx, ny] != -1
                            and reservation_grid[next_t, state.x, state.y] != -1
                            and reservation_grid[state.t, nx, ny]
                            == reservation_grid[next_t, state.x, state.y]
                        )
                    ):
                        heapq.heappush(
                            open_list,
                            (
                                next_t
                                + self.heuristic((nx, ny), goal, state.goal_reached),
                                PathPlannerState(
                                    nx,
                                    ny,
                                    state.theta,
                                    next_t,
                                    DIR_NAMES[state.theta],
                                    state.goal_reached or (nx, ny) == goal,
                                ),
                                new_path,
                            ),
                        )
        # print("\t\tASTAR [No valid path found in given time horizon]")
        return None

    def convert_path_to_route(
        self, path: Optional[List[PathPlannerState]]
    ) -> Optional[List[str]]:
        if path is None:
            return None
        return [s.action for s in path if s.action is not None][1:]  # skip start state

    def convert_route_to_path(self, agent: "Agent") -> Optional[List[PathPlannerState]]:
        """
        Reconstruct a path (list of PathPlannerState) from a start state and action list.

        start: (x, y, theta)
        actions: list of actions (e.g. ["T", "A", "C", "N", ...])
        """
        if agent.route is None:
            return None

        path: List[PathPlannerState] = []
        x: int = agent.current_position[0]
        y: int = agent.current_position[1]
        theta: int = agent.current_orientation
        t: int = 0

        # include start state
        path.append(PathPlannerState(x, y, theta, t, "start"))
        for action in agent.route:
            t += 1
            if action == "T":  # wait
                pass
            elif action == "A":  # rotate left
                theta = (theta - 1) % 4
            elif action == "C":  # rotate right
                theta = (theta + 1) % 4
            else:
                # assume forward movement (N/E/S/W from DIR_NAMES)
                dx, dy = DIRS[theta]
                x += dx
                y += dy
            path.append(PathPlannerState(x, y, theta, t, action))

        return path
