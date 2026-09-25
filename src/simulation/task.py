from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.simulation.agent import Agent
    from src.simulation.environment import Environment
    from src.simulation.geometry import Grid


class Task:
    def __init__(
        self, environment: "Environment", task_id: int, grid: "Grid", time: int
    ):
        self.id: int = task_id
        self.grid: "Grid" = grid
        # this is to make sure that no origin or destination is set to the origin or destination of any other task or current position of robot
        # this facilitate solving path planning and less often gets aborted
        from_pos = grid.get_random_empty_square_no_tasks(
            environment, rng=environment.rng
        )
        if from_pos is None:
            # print(grid.occupancy_grid)
            raise Exception("No valid start position for task found")
        self.from_position: List[int] = from_pos

        to_pos = grid.get_random_empty_square_no_tasks(
            environment, pos=self.from_position, rng=environment.rng
        )
        if to_pos is None:
            # print(grid.occupancy_grid)
            raise Exception("No valid end position for task found")
        self.to_position: List[int] = to_pos

        self.current_position: List[int] = self.from_position.copy()
        #######################################################################
        self.assigned_agent: Optional["Agent"] = None
        self.spawned_time: int = time
        self.assigned_time: Optional[int] = None
        self.pickup_time: Optional[int] = None
        self.completed_time: Optional[int] = None
        #######################################################################
        self.minimum_pickup_time: int = 0
        self.minimum_task_time: int = 0

    def is_assigned(self) -> bool:
        return self.assigned_agent is not None

    def is_finished(self) -> bool:
        return (
            self.current_position == self.to_position
            and self.assigned_agent is not None
        )
