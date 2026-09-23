"""CONFLICT BASED SEARCH (CBS)"""

from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING


import heapq
import itertools
import numpy as np
from src.planners.astar import AStarPathPlanner

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from src.planners.astar import PathPlannerState


class CBS_Constraint:
    def __init__(self, agent: int, x: int, y: int, t: int):
        self.agent: int = agent
        self.x: int = x
        self.y: int = y
        self.t: int = t

    def __lt__(self, other: CBS_Constraint) -> bool:
        return self.t < other.t


class CBS_Node:
    def __init__(self) -> None:
        self.constraints: List[CBS_Constraint] = []
        self.paths: List[List[PathPlannerState]] = []
        self.cost: int = 0

    def __lt__(self, other: CBS_Node) -> bool:
        return self.cost < other.cost


class Planner_CBS:
    """
    This is the implementation of conflict based search (CBS).
    This algorithm plans paths using A* algorithm for multiple agents simultaneously
    that cannot cross each other, and need to consider each other when planning and
    executing their trajectory.

    Every branch (CBS_Node) of the search tree represents a set of different paths for all agents.
    The goal is find a set of paths (plan) that minimizes collective travel time.
    """

    def __init__(
        self,
        grid: NDArray[np.int_],
        cbs_params: Dict[str, Any],
        astar_params: Dict[str, Any],
    ):
        self.grid: NDArray[np.int_] = grid
        self.cbs_params: Dict[str, Any] = cbs_params
        self.astar_planner: AStarPathPlanner = AStarPathPlanner(
            grid, astar_params=astar_params
        )

    def detect_conflict(
        self, paths: List[List[PathPlannerState]]
    ) -> Optional[Dict[str, Any]]:
        max_len: int = max(len(p) for p in paths) if paths else 0

        # Check vertex conflicts (same cell at same time) and
        # "just-vacated" conflicts (one agent at cell at time t and another at same cell at time t+1).
        for t in range(max_len):
            positions_t: Dict[Tuple[int, int], int] = {}
            positions_t1: Dict[Tuple[int, int], int] = {}

            for i, path in enumerate(paths):
                # position at time t
                s_t: Optional[PathPlannerState]
                if t < len(path):
                    s_t = path[t]
                elif t < len(path) + self.cbs_params["MAX_IDLE_TIME_CONSIDERED"]:
                    s_t = path[-1]
                else:
                    s_t = None

                # position at time t+1
                s_t1: Optional[PathPlannerState]
                if t + 1 < len(path):
                    s_t1 = path[t + 1]
                elif t + 1 < len(path) + self.cbs_params["MAX_IDLE_TIME_CONSIDERED"]:
                    s_t1 = path[-1]
                else:
                    s_t1 = None

                if s_t is not None:
                    pos_t: Tuple[int, int] = (s_t.x, s_t.y)

                    # vertex conflict at time t
                    if pos_t in positions_t:
                        return {
                            "time1": t,
                            "time2": t,
                            "a1": positions_t[pos_t],
                            "a2": i,
                            "pos": pos_t,
                        }
                    positions_t[pos_t] = i

                if s_t1 is not None:
                    pos_t1: Tuple[int, int] = (s_t1.x, s_t1.y)

                    # multiple agents at same cell at time t+1 (vertex conflict at t+1)
                    if pos_t1 in positions_t1:
                        return {
                            "time1": t + 1,
                            "time2": t + 1,
                            "a1": positions_t1[pos_t1],
                            "a2": i,
                            "pos": pos_t1,
                        }
                    positions_t1[pos_t1] = i

            # now check for "just-vacated" conflicts: cell occupied at t by agent A and at t+1 by agent B
            for pos, a_at_t in positions_t.items():
                if pos in positions_t1:
                    a_at_t1 = positions_t1[pos]
                    if a_at_t != a_at_t1:
                        return {
                            "time1": t,
                            "time2": t + 1,
                            "a1": a_at_t,
                            "a2": a_at_t1,
                            "pos": pos,
                        }

        return None

    def compute_cost(self, paths: List[List[PathPlannerState]]) -> int:
        return sum(len(p) for p in paths)

    def get_reservation_grid(
        self, constraints: List[CBS_Constraint], agent: int
    ) -> NDArray[np.int_]:
        reservation_grid: NDArray[np.int_] = np.full(
            (
                self.astar_planner.astar_params["planning_horizon"] + 1,
                self.grid.shape[0],
                self.grid.shape[1],
            ),
            -1,
            dtype=int,
        )

        for c in constraints:
            if c.agent == agent:
                reservation_grid[c.t, c.x, c.y] = c.agent
                # note: do not automatically block c.t+1 here — constraints are per-agent and
                # the CBS branching creates explicit constraints for the other agent at t+1 when
                # a "just-vacated" conflict is detected. Blocking c.t+1 here would over-constrain.

        return reservation_grid

    def astar_launcher(
        self,
        start: Tuple[int, int, int],
        goal: Tuple[int, int],
        agent: int,
        constraints: List[CBS_Constraint],
    ) -> Optional[List[PathPlannerState]]:
        # Build reservation grid from constraints
        reservation_grid = self.get_reservation_grid(constraints, agent)
        return self.astar_planner.astar(
            start=start, goal=goal, reservation_grid=reservation_grid
        )

    def plan_cbs(
        self, starts: List[Tuple[int, int, int]], goals: List[Tuple[int, int]]
    ) -> Optional[List[List[PathPlannerState]]]:
        root: CBS_Node = CBS_Node()

        # initial paths
        for i, start in enumerate(starts):
            path = self.astar_launcher(start, goals[i], i, root.constraints)
            if path is None:
                return None
            root.paths.append(path)
        root.cost = self.compute_cost(root.paths)

        # branch and search, avoid conflicts, minize total costs
        open_list: List[Tuple[int, int, CBS_Node]] = []
        counter = itertools.count()
        heapq.heappush(open_list, (root.cost, next(counter), root))
        nodes_expanded: int = 0

        while open_list:
            _, _, node = heapq.heappop(open_list)
            nodes_expanded += 1

            # ABORT CONDITION: TIMEOUT
            if nodes_expanded > self.cbs_params["max_iterations"]:
                print("\t\t CBS [TIMEOUT]")
                return None

            # Detect conflicts
            conflict = self.detect_conflict(node.paths)

            # Determine valid set of paths
            if conflict is None:
                return node.paths

            # Explore other paths for conflicts
            for agent in [conflict["a1"], conflict["a2"]]:
                child: CBS_Node = CBS_Node()
                child.constraints = list(node.constraints)
                x, y = conflict["pos"]

                # use per-agent time (allows detecting and constraining t and t+1 differently)
                t: int = (
                    conflict["time1"] if agent == conflict["a1"] else conflict["time2"]
                )
                child.constraints.append(CBS_Constraint(agent, x, y, t))
                child.paths = list(node.paths)
                start_state: PathPlannerState = child.paths[agent][0]
                start_pos: Tuple[int, int, int] = (
                    start_state.x,
                    start_state.y,
                    start_state.theta,
                )
                new_path = self.astar_launcher(
                    start_pos, goals[agent], agent, child.constraints
                )
                if new_path is None:
                    continue
                child.paths[agent] = new_path
                child.cost = self.compute_cost(child.paths)
                heapq.heappush(open_list, (child.cost, next(counter), child))
        print(
            "\t\tCBS [No conflict-free set of paths could be found in given time horizon]"
        )
        return None

    def convert_paths_to_routes(
        self, paths: Optional[List[List[PathPlannerState]]]
    ) -> Optional[List[List[str]]]:
        routes: List[List[str]] = []
        if paths is None:
            return None
        for i, p in enumerate(paths):
            route: List[str] = [s.action for s in p if s.action is not None][1:]
            routes.append(route)
        return routes

    def plan(
        self, starts: List[Tuple[int, int, int]], goals: List[Tuple[int, int]]
    ) -> Optional[List[List[str]]]:
        paths = self.plan_cbs(starts, goals)
        return self.convert_paths_to_routes(paths)
