from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.simulation.agent import Agent
    from src.simulation.environment import Environment
    from src.planners.astar import PathPlannerState
    from numpy.typing import NDArray


from src.simulation.constants import (
    AGENT_ORIENTATION_EAST,
    AGENT_ORIENTATION_WEST,
    AGENT_ORIENTATION_NORTH,
    AGENT_ORIENTATION_SOUTH,
)

import numpy as np
from src.simulation.constants import (
    SQUARE_SYMBOL_EMPTY,
    SQUARE_SYMBOL_OCCUPIED,
    SPAWN_BORDER,
    SPAWN_OCCUPIED_CELLS_BORDER,
)


class GridTools:
    @staticmethod
    def _state_at_time(
        path: List[PathPlannerState], t: int
    ) -> Optional[PathPlannerState]:
        if len(path) == 0:
            return None
        if t < len(path):
            return path[t]
        return path[-1]

    @staticmethod
    def create_3D_reservation_grid(
        environment: Environment,
        time_horizon: int,
        agent_list: Optional[List[Agent]] = None,
        tabu_agent: Optional[Agent] = None,
    ) -> NDArray[np.int_]:
        """Create a 3D reservation table (time,x,y) storing agent ids; -1 means free."""
        reservation_table: NDArray[np.int_] = np.full(
            (time_horizon + 1, environment.grid.grid_size, environment.grid.grid_size),
            -1,
            dtype=int,
        )

        if agent_list is None:
            agent_list = environment.agents.copy()

        for agent in agent_list:
            if tabu_agent is not None and agent == tabu_agent:
                continue

            # init
            time_counter: int = 0
            current_pos: List[int] = agent.current_position.copy()

            # first position
            if time_counter < reservation_table.shape[0]:
                reservation_table[time_counter][current_pos[0]][
                    current_pos[1]
                ] = agent.id
            time_counter += 1

            # part of route
            for step in agent.route:
                if step == "C" or step == "A" or step == "T":
                    pass
                elif step == "N":
                    current_pos[1] += 1
                elif step == "S":
                    current_pos[1] -= 1
                elif step == "E":
                    current_pos[0] += 1
                elif step == "W":
                    current_pos[0] -= 1

                if time_counter < reservation_table.shape[0]:
                    reservation_table[time_counter][current_pos[0]][
                        current_pos[1]
                    ] = agent.id
                time_counter += 1
                if time_counter == reservation_table.shape[0]:
                    break

            # end
            while time_counter < reservation_table.shape[0]:
                reservation_table[time_counter][current_pos[0]][
                    current_pos[1]
                ] = agent.id
                time_counter += 1
        return reservation_table

    @staticmethod
    def detect_conflicts(
        path: List[PathPlannerState],
        agent_list: List[Agent],
        time_horizon: int,
        tabu_agent: Optional[Agent] = None,
    ) -> List[Dict[str, Any]]:
        conflicts: List[Dict[str, Any]] = []
        conflicting_agents: List[int] = []
        if len(path) == 0:
            return conflicts

        for agent in agent_list:
            if tabu_agent is not None and agent == tabu_agent:
                continue

            other_path = agent.path_planner.convert_route_to_path(agent)
            if other_path is None or len(other_path) == 0:
                continue

            max_t = min(time_horizon, max(path[-1].t, other_path[-1].t))
            for t in range(max_t + 1):
                my_state = GridTools._state_at_time(path, t)
                other_state = GridTools._state_at_time(other_path, t)
                if my_state is None or other_state is None:
                    continue

                my_pos = (my_state.x, my_state.y)
                other_pos = (other_state.x, other_state.y)
                if my_pos == other_pos:
                    if agent.id not in conflicting_agents:
                        conflicts.append(
                            {
                                "time": t,
                                "position": my_pos,
                                "conflicting_agent": agent.id,
                                "type": "vertex",
                            }
                        )
                        conflicting_agents.append(agent.id)
                    break

                if t == 0:
                    continue

                my_prev = GridTools._state_at_time(path, t - 1)
                other_prev = GridTools._state_at_time(other_path, t - 1)
                if my_prev is None or other_prev is None:
                    continue

                my_prev_pos = (my_prev.x, my_prev.y)
                other_prev_pos = (other_prev.x, other_prev.y)
                if my_prev_pos == other_pos and other_prev_pos == my_pos:
                    if agent.id not in conflicting_agents:
                        conflicts.append(
                            {
                                "time": t,
                                "position": my_pos,
                                "conflicting_agent": agent.id,
                                "type": "edge",
                            }
                        )
                        conflicting_agents.append(agent.id)
                    break
        return conflicts


class Grid:
    def __init__(self, grid_size: int):
        self.grid_size: int = grid_size
        self.occupancy_grid: NDArray[np.int_] = SQUARE_SYMBOL_EMPTY * np.ones(
            (grid_size, grid_size), dtype=int
        )

    def get_random_empty_square(self, rng: Optional[Any] = None) -> Optional[List[int]]:
        empty_indices = np.argwhere(self.occupancy_grid == SQUARE_SYMBOL_EMPTY)
        if empty_indices.size == 0:
            return None
        if rng is None:
            rng = np.random
        idx: int = int(rng.choice(len(empty_indices)))
        x, y = empty_indices[idx]
        return [int(x), int(y)]

    @staticmethod
    def _occupy_with_border(
        grid: NDArray[np.int_], x: int, y: int, border: int, occupied_symbol: int
    ) -> None:
        max_x: int = len(grid)
        max_y: int = len(grid[0])
        for dx in range(-border, border + 1):
            for dy in range(-border, border + 1):
                nx: int = x + dx
                ny: int = y + dy
                if 0 <= nx < max_x and 0 <= ny < max_y:
                    grid[nx][ny] = occupied_symbol

    def get_random_empty_square_no_tasks(
        self,
        environment: Environment,
        pos: Optional[List[int]] = None,
        rng: Optional[Any] = None,
    ) -> Optional[List[int]]:
        temp_occupancy_grid: NDArray[np.int_] = self.occupancy_grid.copy()

        # other tasks
        for task in environment.tasks:
            Grid._occupy_with_border(
                temp_occupancy_grid,
                task.from_position[0],
                task.from_position[1],
                SPAWN_OCCUPIED_CELLS_BORDER,
                SQUARE_SYMBOL_OCCUPIED,
            )
            Grid._occupy_with_border(
                temp_occupancy_grid,
                task.to_position[0],
                task.to_position[1],
                SPAWN_OCCUPIED_CELLS_BORDER,
                SQUARE_SYMBOL_OCCUPIED,
            )

        # other agents
        for agent in environment.agents:
            Grid._occupy_with_border(
                temp_occupancy_grid,
                agent.current_position[0],
                agent.current_position[1],
                SPAWN_OCCUPIED_CELLS_BORDER,
                SQUARE_SYMBOL_OCCUPIED,
            )

        # additional points
        if pos is not None:
            Grid._occupy_with_border(
                temp_occupancy_grid,
                pos[0],
                pos[1],
                SPAWN_OCCUPIED_CELLS_BORDER,
                SQUARE_SYMBOL_OCCUPIED,
            )

        # spawn border
        for idx in range(0, SPAWN_BORDER):
            temp_occupancy_grid[idx, :] = SQUARE_SYMBOL_OCCUPIED
            temp_occupancy_grid[self.grid_size - 1 - idx, :] = SQUARE_SYMBOL_OCCUPIED
            temp_occupancy_grid[:, idx] = SQUARE_SYMBOL_OCCUPIED
            temp_occupancy_grid[:, self.grid_size - 1 - idx] = SQUARE_SYMBOL_OCCUPIED

        # determine empty spaces for candidates
        empty_indices = np.argwhere(temp_occupancy_grid == SQUARE_SYMBOL_EMPTY)
        if empty_indices.size == 0:
            return None

        if rng is None:
            rng = environment.rng

        idx = int(rng.choice(len(empty_indices)))
        x, y = empty_indices[idx]
        return [int(x), int(y)]

    def occupy(self, position: List[int]) -> None:
        self.occupancy_grid[position[0], position[1]] = SQUARE_SYMBOL_OCCUPIED

    def release(self, position: List[int]) -> None:
        self.occupancy_grid[position[0], position[1]] = SQUARE_SYMBOL_EMPTY


class Geometry:
    @staticmethod
    def mahattan_distance(
        position_a: Tuple[int, int], position_b: Tuple[int, int]
    ) -> int:
        a_x, a_y = position_a
        b_x, b_y = position_b
        return abs(a_x - b_x) + abs(a_y - b_y)

    @staticmethod
    def rotation_distance(start_orientation: int, required_orientation: int) -> int:
        """Minimum number of rotations between two orientations."""
        diff: int = abs(start_orientation - required_orientation)
        return min(diff, 4 - diff)

    @staticmethod
    def travel_time_with_rotation(
        position_a: Tuple[int, int], position_b: Tuple[int, int], start_orientation: int
    ) -> int:
        """Estimate travel time including rotation cost."""
        ax, ay = position_a
        bx, by = position_b
        dx: int = bx - ax
        dy: int = by - ay
        move_cost: int = abs(dx) + abs(dy)
        # if already there
        if move_cost == 0:
            return 0
        # determine required first movement direction
        if abs(dx) > abs(dy):
            if dx > 0:
                needed_orientation = AGENT_ORIENTATION_EAST
            else:
                needed_orientation = AGENT_ORIENTATION_WEST
        else:
            if dy > 0:
                needed_orientation = AGENT_ORIENTATION_NORTH
            else:
                needed_orientation = AGENT_ORIENTATION_SOUTH
        rotation_cost: int = Geometry.rotation_distance(
            start_orientation, needed_orientation
        )
        return move_cost + rotation_cost
