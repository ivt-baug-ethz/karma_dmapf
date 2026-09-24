from __future__ import annotations
from typing import List, Optional, Tuple, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from src.simulation.task import Task
    from src.simulation.environment import Environment
    from src.simulation.geometry import Grid
    from src.planners.astar import PathPlannerState


import numpy as np
from src.planners.astar import AStarPathPlanner
from src.simulation.constants import (
    AGENT_ORIENTATIONS,
    AGENT_STATUS_CARRY,
    AGENT_STATUS_PICKUP,
    AGENT_STATUS_IDLE,
)
from src.simulation.constants import (
    AGENT_ORIENTATION_SOUTH,
    AGENT_ORIENTATION_NORTH,
    AGENT_ORIENTATION_EAST,
    AGENT_ORIENTATION_WEST,
)
from src.simulation.constants import (
    COST_TO_CHANGE_INFEASIBLE,
    IDLING_NEIGHBORHOOD_SEARCH_RANGE,
)
from src.simulation.geometry import GridTools


class Agent:
    def __init__(self, agent_id: int, environment: "Environment"):
        self.id: int = agent_id
        self.environment: "Environment" = environment
        self.grid: "Grid" = self.environment.grid

        pos = self.grid.get_random_empty_square(rng=self.environment.rng)
        if pos is None:
            raise ValueError("No empty square available for agent spawning.")

        self.current_position: List[int] = pos
        self.current_orientation: int = int(
            self.environment.rng.choice(AGENT_ORIENTATIONS)
        )
        self.assigned_task: Optional["Task"] = None
        self.status: int = AGENT_STATUS_IDLE
        self.route: List[str] = []
        self.target_position: List[int] = []
        self.minimal_path_cost: Optional[int] = None
        self.grid.occupy(self.current_position)
        self.path_planner: AStarPathPlanner = AStarPathPlanner(
            static_occupancy_grid=self.environment.static_grid.occupancy_grid,
            astar_params=self.environment.settings["params_astar"],
        )
        self.karma_balance: int = self.environment.settings["params_karma"][
            "initial_karma"
        ]

    def is_idle(self) -> bool:
        return self.assigned_task is None

    def is_available_soon(self) -> bool:
        return self.status == AGENT_STATUS_CARRY

    def release_task(self) -> None:
        self.assigned_task = None
        self.status = AGENT_STATUS_IDLE
        self.target_position = []
        self.minimal_path_cost = None

    def get_forecasted_path_total_cost(self):
        if self.assigned_task is None:
            return 0
        time_so_far = self.environment.time - self.assigned_task.spawned_time
        if self.status == AGENT_STATUS_CARRY:
            return time_so_far + len(self.route)
        elif self.status == AGENT_STATUS_PICKUP:
            carry_path = self._compute_shortest_path(
                start=(
                    self.assigned_task.from_position[0],
                    self.assigned_task.from_position[1],
                    0,
                ),
                goal=self.assigned_task.to_position,
            )
            carry_time = len(carry_path)
            return time_so_far + len(self.route) + carry_time
        else:
            return None

    def assign_task(self, task: "Task", time: int) -> None:
        self.assigned_task = task
        self.minimal_path_cost = self._compute_minimal_path_cost()
        self.target_position = task.from_position
        if self.current_position == task.from_position:
            self.status = AGENT_STATUS_CARRY

            if self.assigned_task.pickup_time is None:
                self.assigned_task.pickup_time = time
                self.assigned_task.minimum_task_time = self._compute_minimum_task_time()

                # if strategy requires, reset Karma balance on pickup
                if (
                    self.environment.settings["mapf_control"]
                    == "DECENTRALIZED_NEGOTIATE_TRIP_KARMA"
                ):
                    self.karma_balance = self.environment.settings["params_karma"][
                        "initial_karma"
                    ]
        else:
            self.status = AGENT_STATUS_PICKUP

    def _get_evaluation_horizon(self) -> int:
        return max(
            self.environment.settings["params_astar"]["planning_horizon"],
            4 * (self.grid.grid_size**2),
        )

    def _compute_shortest_path(
        self, start: Tuple[int, int, int], goal: List[int]
    ) -> List["PathPlannerState"]:
        path = self.path_planner.astar(
            start=start,
            goal=(goal[0], goal[1]),
            reservation_grid=None,
            ignore_counter=True,
            planning_horizon=self._get_evaluation_horizon(),
        )
        if path is None:
            raise ValueError(
                f"Could not compute shortest path from {start[:2]} to {goal}."
            )
        return path

    def _compute_minimal_path_cost(self) -> int:
        if self.assigned_task is None:
            raise ValueError("Cannot compute minimal path cost without assigned task.")

        pickup_path = self._compute_shortest_path(
            start=(
                self.current_position[0],
                self.current_position[1],
                self.current_orientation,
            ),
            goal=self.assigned_task.from_position,
        )
        pickup_state = pickup_path[-1]
        delivery_path = self._compute_shortest_path(
            start=(pickup_state.x, pickup_state.y, pickup_state.theta),
            goal=self.assigned_task.to_position,
        )

        return len(pickup_path) + len(delivery_path)

    def update_target_position(self, time: int) -> None:
        # determine target
        if self.status == AGENT_STATUS_PICKUP:
            if self.assigned_task:
                self.target_position = self.assigned_task.from_position
            else:
                raise ValueError("Agent in PICKUP status without assigned task.")

        elif self.status == AGENT_STATUS_CARRY:
            if self.assigned_task:
                self.target_position = self.assigned_task.to_position
            else:
                raise ValueError("Agent in CARRY status without assigned task.")

        # update status in case hit
        if self.current_position == self.target_position:
            self.status = AGENT_STATUS_CARRY
            if self.assigned_task:
                self.target_position = self.assigned_task.to_position

                # if the task was only picked up now, set pickup time
                if self.assigned_task.pickup_time is None:
                    self.assigned_task.pickup_time = time
                    self.assigned_task.minimum_task_time = (
                        self._compute_minimum_task_time()
                    )

                    # if strategy requires, reset Karma balance on pickup
                    if (
                        self.environment.settings["mapf_control"]
                        == "DECENTRALIZED_NEGOTIATE_TRIP_KARMA"
                    ):
                        self.karma_balance = self.environment.settings["params_karma"][
                            "initial_karma"
                        ]

            else:
                raise ValueError("Agent in CARRY status without assigned task.")

    def _compute_minimum_task_time(self) -> int:
        if self.assigned_task is None:
            raise ValueError("Cannot compute minimum task time without assigned task.")
        path = self._compute_shortest_path(
            start=(
                self.current_position[0],
                self.current_position[1],
                self.current_orientation,
            ),
            goal=self.assigned_task.to_position,
        )
        if path:
            return path[-1].t

        raise ValueError(
            "Could not compute minimum task time: No path found from {} to {}.".format(
                self.current_position, self.assigned_task.to_position
            )
        )

    def execute_route(self) -> None:
        if len(self.route) > 0:
            task = self.route[0]
            self.route = self.route[1:]
            if task == "N":
                self._move_north()
            if task == "E":
                self._move_east()
            if task == "S":
                self._move_south()
            if task == "W":
                self._move_west()
            if task == "C":
                self._rotate_clockwise()
            if task == "A":
                self._rotate_counter_clockwise()
            if task == "T":
                pass

            if self.status == AGENT_STATUS_CARRY and self.assigned_task:
                self.assigned_task.current_position = self.current_position
            elif self.status == AGENT_STATUS_CARRY and not self.assigned_task:
                raise ValueError("Agent in CARRY status without assigned task.")

    def _move_north(self) -> None:
        if (
            self.current_position[1] < self.grid.grid_size - 1
            and self.current_orientation == AGENT_ORIENTATION_NORTH
        ):
            self.grid.release(self.current_position)
            self.current_position[1] += 1
            self.grid.occupy(self.current_position)

    def _move_east(self) -> None:
        if (
            self.current_position[0] < self.grid.grid_size - 1
            and self.current_orientation == AGENT_ORIENTATION_EAST
        ):
            self.grid.release(self.current_position)
            self.current_position[0] += 1
            self.grid.occupy(self.current_position)

    def _move_south(self) -> None:
        if (
            self.current_position[1] > 0
            and self.current_orientation == AGENT_ORIENTATION_SOUTH
        ):
            self.grid.release(self.current_position)
            self.current_position[1] -= 1
            self.grid.occupy(self.current_position)

    def _move_west(self) -> None:
        if (
            self.current_position[0] > 0
            and self.current_orientation == AGENT_ORIENTATION_WEST
        ):
            self.grid.release(self.current_position)
            self.current_position[0] -= 1
            self.grid.occupy(self.current_position)

    def _rotate_clockwise(self) -> None:
        self.current_orientation += 1
        if self.current_orientation > AGENT_ORIENTATION_WEST:
            self.current_orientation = AGENT_ORIENTATION_NORTH

    def _rotate_counter_clockwise(self) -> None:
        self.current_orientation -= 1
        if self.current_orientation < AGENT_ORIENTATION_NORTH:
            self.current_orientation = AGENT_ORIENTATION_WEST

    def _determine_intersection_free_path(
        self, reservation_grid: NDArray[np.int_]
    ) -> Optional[List["PathPlannerState"]]:
        if not self.target_position:
            return None

        path = self.path_planner.astar(
            start=(
                self.current_position[0],
                self.current_position[1],
                self.current_orientation,
            ),
            goal=(self.target_position[0], self.target_position[1]),
            reservation_grid=reservation_grid,
        )
        return path

    def _determine_idle_parking_path(
        self, reservation_grid: NDArray[np.int_]
    ) -> Optional[List["PathPlannerState"]]:
        x0, y0 = self.current_position

        # determine empty cells for idling nearby
        target_candidates: List[List[int]] = []
        for dx in range(
            -IDLING_NEIGHBORHOOD_SEARCH_RANGE, IDLING_NEIGHBORHOOD_SEARCH_RANGE + 1
        ):
            for dy in range(
                -IDLING_NEIGHBORHOOD_SEARCH_RANGE, IDLING_NEIGHBORHOOD_SEARCH_RANGE + 1
            ):
                # skip the current cell itself
                if dx == 0 and dy == 0:
                    continue

                # explore probe
                probe_pos_x = x0 + dx
                probe_pos_y = y0 + dy

                # grid bounds check
                if probe_pos_x < 0 or probe_pos_y < 0:
                    continue

                if (
                    probe_pos_x >= reservation_grid.shape[1]
                    or probe_pos_y >= reservation_grid.shape[2]
                ):
                    continue

                # cell must be free at all times in the horizon
                column = reservation_grid[:, probe_pos_x, probe_pos_y]
                if np.equal(column, -1).all():
                    target_candidates.append([probe_pos_x, probe_pos_y])

        # sort them closest to origin (self.current_position)
        target_candidates.sort(
            key=lambda p: (p[0] - x0) ** 2 + (p[1] - y0) ** 2
        )  # squared distance is enough for ordering[web:19][web:22]

        # if some found, check if there is a path to one
        for target_candidate in target_candidates:
            path = self.path_planner.astar(
                start=(
                    self.current_position[0],
                    self.current_position[1],
                    self.current_orientation,
                ),
                goal=(target_candidate[0], target_candidate[1]),
                reservation_grid=reservation_grid,
            )
            if path is not None:
                return path

        return None

    def plan_route_decentralized_token_passing(self) -> None:
        # token-passing: determine reservation grid given all already planned routes
        reservation_grid = GridTools.create_3D_reservation_grid(
            environment=self.environment,
            time_horizon=self.environment.get_sufficient_planning_horizon(),
            agent_list=self.environment.agents,
            tabu_agent=self,
        )

        # determine possible, intersection free path
        path = self._determine_intersection_free_path(reservation_grid)
        if path is not None:
            route = self.path_planner.convert_path_to_route(path)
            self.route = route if route is not None else []
        else:
            self.route = []

    def determine_cost_to_change(
        self, to_avoid_path: List["PathPlannerState"]
    ) -> Tuple[float, Optional[List["PathPlannerState"]]]:
        current_cost = len(self.route)

        # determine reservation_grid given all already planned routes
        reservation_grid = GridTools.create_3D_reservation_grid(
            environment=self.environment,
            time_horizon=self.environment.get_sufficient_planning_horizon(),
            agent_list=self.environment.agents,
            tabu_agent=self,
        )

        # add to_avoid_path to reservation grid, marking only free cells (-1) so that the ids of
        # other agents stay intact for the swap (edge conflict) check in A*
        for state in to_avoid_path:
            if (
                state.t < reservation_grid.shape[0]
                and reservation_grid[state.t][state.x][state.y] == -1
            ):
                reservation_grid[state.t][state.x][state.y] = self.id
        last_state = to_avoid_path[-1]

        # inifinite remaining on that position after path execution
        for t in range(last_state.t, reservation_grid.shape[0]):
            if reservation_grid[t][last_state.x][last_state.y] == -1:
                reservation_grid[t][last_state.x][last_state.y] = self.id

        # if you have a target
        changed_path: Optional[List["PathPlannerState"]] = None

        if len(self.target_position) > 0:
            # determine possible, intersection free path
            changed_path = self._determine_intersection_free_path(reservation_grid)
            if changed_path is not None:
                changed_route = self.path_planner.convert_path_to_route(changed_path)
                changed_cost = len(changed_route if changed_route else [])
                return (changed_cost - current_cost), changed_path
            else:
                return COST_TO_CHANGE_INFEASIBLE, changed_path

        else:
            # determine if there is any free position nearby to idle parking
            changed_path = self._determine_idle_parking_path(reservation_grid)
            if changed_path is not None:
                parking_route = self.path_planner.convert_path_to_route(changed_path)
                parking_cost = len(parking_route if parking_route else [])
                return (parking_cost - current_cost), changed_path
            else:
                return COST_TO_CHANGE_INFEASIBLE, changed_path

    def change_path_to_satisfy(self, change_to_path: List["PathPlannerState"]) -> None:
        alternative_route = self.path_planner.convert_path_to_route(change_to_path)
        self.route = alternative_route if alternative_route else []
