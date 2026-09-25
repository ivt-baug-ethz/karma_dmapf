from __future__ import annotations
from typing import Union, List, Optional, Tuple, Dict, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.planners.astar import PathPlannerState

import numpy as np
from src.simulation.constants import (
    COST_TO_CHANGE_INFEASIBLE,
    MAPF_CONTROLLER_CENTRALIZED,
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
)
from src.planners.cbs import Planner_CBS
from src.planners.assignment import Planner_Assignment_Central
from src.simulation.geometry import Grid, GridTools
from src.simulation.task import Task
from src.simulation.negotiation_strategy import NegotiationStrategy
from src.simulation.agent import Agent


class Environment:
    def __init__(self, settings: Dict[str, Any]):
        self.settings: Dict[str, Any] = settings
        self.grid: Grid = Grid(grid_size=self.settings["grid_size"])
        self.static_grid: Grid = Grid(grid_size=self.settings["grid_size"])
        self.rng = np.random.default_rng(self.settings["random_seed"])
        self.time: int = 0
        self.agents: List[Agent] = []
        self.tasks: List[Task] = []
        self.completed_tasks: dict[int, List[Task]] = (
            {}
        )  # mapping: agent_id -> list of completed tasks

    def determine_new_id(self, lst: Union[List[Agent], List[Task]]) -> int:
        last_id = 0
        if len(lst) > 0:
            last_id = lst[-1].id
        return last_id + 1

    def spawn_agent(self) -> None:
        self.agents.append(
            Agent(agent_id=self.determine_new_id(self.agents), environment=self)
        )

    def spawn_task(self) -> None:
        try:
            self.tasks.append(
                Task(
                    environment=self,
                    task_id=self.determine_new_id(self.tasks),
                    grid=self.grid,
                    time=self.time,
                )
            )
        except Exception as e:
            if self.settings["debug_statements"]:
                print("Exception:", e)
                print("Grid is too crowded, cannot spawn new task at the moment.")
            pass

    def assign_open_tasks(self) -> None:
        candidate_agents: List[Agent] = [
            a for a in self.agents if a.is_idle() or a.is_available_soon()
        ]
        open_tasks: List[Task] = [t for t in self.tasks if not t.is_assigned()]
        if not candidate_agents or not open_tasks:
            return

        agent_indices, task_indices = Planner_Assignment_Central.plan_assignment(
            candidate_agents, open_tasks, self.time
        )

        for a_idx, t_idx in zip(agent_indices, task_indices):
            agent: Agent = candidate_agents[a_idx]
            task: Task = open_tasks[t_idx]

            # only assign if agent is idle (otherwise it is done in later iteration)
            if agent.is_idle():
                agent.assign_task(task=task, time=self.time)
                task.assigned_agent = agent

    def close_finished_tasks(self) -> bool:
        finished_tasks: List[Task] = [task for task in self.tasks if task.is_finished()]

        for task in finished_tasks:
            if task.assigned_agent:
                task.assigned_agent.release_task()
            else:
                raise Exception(
                    f"Task {task.id} is finished but has no assigned agent."
                )

            self.tasks.remove(task)
            task.completed_time = self.time
            if task.assigned_agent.id not in self.completed_tasks:
                self.completed_tasks[task.assigned_agent.id] = []
            self.completed_tasks[task.assigned_agent.id].append(task)

        return len(finished_tasks) > 0

    def handle_agents(self) -> None:
        # ROUTE EXECTUION: update agent target and status
        self.handle_agents_route_execution()

        # ROUTE PLANNING: for those who need
        if self.settings["mapf_control"] == MAPF_CONTROLLER_CENTRALIZED:
            self.handle_agents_route_planning_centralized()
        elif (
            self.settings["mapf_control"] == MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING
        ):
            self.handle_agents_route_planning_decentralized_token_passing()
        elif (
            self.settings["mapf_control"]
            == MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC
        ):
            self.handle_agents_route_planning_decentralized_negotiate(
                NegotiationStrategy.negotiate_egoistic
            )
        elif (
            self.settings["mapf_control"]
            == MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN
        ):
            self.handle_agents_route_planning_decentralized_negotiate(
                lambda cost_other, cost_mine: NegotiationStrategy.negotiate_utilitarian(
                    cost_other, cost_mine, rng=self.rng
                )
            )
        elif (
            self.settings["mapf_control"]
            == MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA
        ):
            self.handle_agents_route_planning_decentralized_negotiate(
                NegotiationStrategy.negotiate_karma, use_agent_params=True
            )
        elif (
            self.settings["mapf_control"]
            == MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA
        ):
            self.handle_agents_route_planning_decentralized_negotiate(
                NegotiationStrategy.negotiate_karma, use_agent_params=True
            )

    def handle_agents_route_execution(self) -> None:
        for agent in self.agents:
            agent.execute_route()

            # an agent passing over its pickup cell picks up there and keeps its reserved route
            if not agent.is_idle() and (
                len(agent.route) == 0 or agent.current_position == agent.target_position
            ):
                agent.update_target_position(self.time)

    def print_debug_log(self) -> None:
        if self.settings["debug_statements"]:
            print("")
            print("\tOpen Routes:")
            planning_relevant_agents: List[Agent] = [
                agent for agent in self.agents if len(agent.route) > 0
            ]

            for agent in planning_relevant_agents:
                print("\t\t", agent.id, agent.route)

            print("\n\tCurrent Agent Positions:")
            for agent in self.agents:
                print(
                    "\t\t",
                    agent.id,
                    "\t",
                    agent.current_position,
                    "\t| ",
                    agent.target_position,
                )
            print("")
            print("")

    def get_agent(self, agent_id: int) -> Optional[Agent]:
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def get_sufficient_planning_horizon(self):
        min_length = 0
        for agent in self.agents:
            min_length = max(min_length, len(agent.route))
        min_length = max(min_length, self.settings["params_astar"]["planning_horizon"])
        min_length += self.settings["params_astar"][
            "planning_horizon_buffer"
        ]  # 20 buffer
        return min_length

    def handle_agents_route_planning_centralized(self) -> None:
        """
        This works as follows: centralised planning according to CBS, meaning optimization on joint state space.
        """
        self.print_debug_log()
        # conduct centralized planning for running agents with jobs
        planning_relevant_agents: List[Agent] = [
            agent for agent in self.agents if not agent.is_idle()
        ]
        if len(planning_relevant_agents) > 0:
            grid = self.grid.occupancy_grid * 0
            starts: List[Tuple[int, int, int]] = [
                (
                    agent.current_position[0],
                    agent.current_position[1],
                    agent.current_orientation,
                )
                for agent in planning_relevant_agents
            ]
            goals: List[Tuple[int, int]] = [
                (agent.target_position[0], agent.target_position[1])
                for agent in planning_relevant_agents
            ]
            planner: Planner_CBS = Planner_CBS(
                grid,
                cbs_params=self.settings["params_cbs"],
                astar_params=self.settings["params_astar"],
            )
            # print("\tInput for Planner:", starts, goals, "\n", grid)
            routes = planner.plan(starts, goals)
            # update routes
            if routes is not None:
                for idx, agent in enumerate(planning_relevant_agents):
                    agent.route = routes[idx]
            else:  # Fallback: DECENTRALIZED_UTILITARIAN
                raise Exception(
                    "Centralized planning failed to find a solution, consider adjusting parameters or using a different controller."
                )

    def handle_agents_route_planning_decentralized_token_passing(self) -> None:
        """
        Token-passing: every new agent plans its route around
        already existing planned routes; no negotiation, just adaptation to others.
        """
        self.print_debug_log()

        # conduct decentralized planning for running agents with jobs who finished their current route
        planning_relevant_agents: List[Agent] = [
            agent
            for agent in self.agents
            if (not agent.is_idle())
            and len(agent.route) == 0
            and len(agent.target_position) == 2
        ]
        for agent in planning_relevant_agents:
            agent.plan_route_decentralized_token_passing()

    def plan_shortest_path_given_considerations(self, agents_considered, agent):
        reservation_grid = GridTools.create_3D_reservation_grid(
            environment=self,
            time_horizon=self.get_sufficient_planning_horizon(),
            agent_list=agents_considered,
            tabu_agent=agent,
        )
        if agent.path_planner is None:
            raise Exception(
                f"Agent {agent.id} has no path planner assigned, cannot plan route."
            )
        current_path = agent.path_planner.astar(
            start=(
                agent.current_position[0],
                agent.current_position[1],
                agent.current_orientation,
            ),
            goal=(agent.target_position[0], agent.target_position[1]),
            reservation_grid=reservation_grid,
        )
        return current_path

    def determine_conflicts(self, current_path, agent):
        # rebuild full reservation table each iteration so we always check conflicts against the
        # latest routes other agents may have switched to during negotiation
        conflicts = GridTools.detect_conflicts(
            current_path,
            agent_list=self.agents,
            time_horizon=self.get_sufficient_planning_horizon(),
            tabu_agent=agent,
        )
        return conflicts

    def prioritize_conflicts(self, conflicts, agents_considered, agent, current_path):
        current_path_cost = len(current_path)
        conflict_costs = []

        for conflict in conflicts:
            conflicting_agent = self.get_agent(conflict["conflicting_agent"])
            if conflicting_agent is None:
                raise Exception(
                    f"Conflict with agent id {conflict['conflicting_agent']} but no such agent found."
                )

            hypothetical_agents_considered = agents_considered.copy()
            hypothetical_agents_considered.append(conflicting_agent)
            hypothetical_path = self.plan_shortest_path_given_considerations(
                hypothetical_agents_considered, agent
            )
            hypothetical_path_cost = (
                len(hypothetical_path)
                if hypothetical_path is not None
                else float("inf")
            )
            conflict_costs.append(hypothetical_path_cost - current_path_cost)

        conflicts = [
            conflict
            for _, conflict in sorted(
                zip(conflict_costs, conflicts), key=lambda item: item[0], reverse=True
            )
        ]
        return conflicts, conflict_costs

    def determine_my_cost(self, agent, conflicting_agent, current_path):
        route = agent.path_planner.convert_path_to_route(current_path)
        original_route = list(agent.route)
        agent.route = route if route else []
        path = conflicting_agent.path_planner.convert_route_to_path(conflicting_agent)
        cost_mine: int = COST_TO_CHANGE_INFEASIBLE
        try:
            if path:
                cost_mine, alternative_path_mine = agent.determine_cost_to_change(
                    to_avoid_path=path
                )
            else:
                raise ValueError(
                    f"Path found for conflicting agent {conflicting_agent.id} but could not be converted to route."
                )
        finally:
            agent.route = original_route
        return cost_mine, alternative_path_mine

    def make_decision(
        self,
        agent,
        conflicting_agent,
        cost_other,
        cost_mine,
        negotiation_function,
        use_agent_params,
    ):
        if use_agent_params:
            other_resolves_conflict = negotiation_function(
                cost_other,
                cost_mine,
                conflicting_agent,
                agent,
                self.settings["params_karma"],
            )
        else:
            # idle agents do not give way under the rules without agent parameters
            if conflicting_agent.is_idle():
                cost_other = COST_TO_CHANGE_INFEASIBLE

            other_resolves_conflict = negotiation_function(cost_other, cost_mine)
        return other_resolves_conflict

    def handle_agents_route_planning_decentralized_negotiate(
        self,
        negotiation_function: Callable,
        use_agent_params: bool = False,
    ) -> None:
        """
        This works as follows: every new agent will plan its route shortest.
        Then checks if it is conflicting with others.
        If not take it.
        If conflicting, negotiate with that specific one...
            - if other agrees (according to negotiation strategy)
                do change for both agents
            - else
                need to replan considering this restriction
        """
        self.print_debug_log()
        # conduct decentralized planning for running agents with jobs who finished their current route
        planning_relevant_agents: List[Agent] = [
            agent
            for agent in self.agents
            if (not agent.is_idle())
            and len(agent.route) == 0
            and len(agent.target_position) == 2
        ]

        for agent in planning_relevant_agents:
            # if due to negotiation already changed...skip
            if len(agent.route) > 0:
                continue

            # try for this agent to plan, given the restrictions it step by step considers
            agents_considered: List[Agent] = []
            current_path: Optional[List[PathPlannerState]] = None
            found_conflict_free_path: bool = False

            # # safety guard to avoid infinite negotiation loops
            max_iterations: int = max(10, len(self.agents) * 2)
            iter_count: int = 0

            # iterate until no open conflicts exist
            while True:
                iter_count += 1
                if iter_count > max_iterations:
                    break

                # determine shortest path (given considered restrictions)
                current_path = self.plan_shortest_path_given_considerations(
                    agents_considered, agent
                )
                if current_path is None:  # if cannot plan, just abort for now
                    break

                # determine conflicts with current plan
                conflicts = self.determine_conflicts(current_path, agent)
                if len(conflicts) == 0:  # if no conflicts, found the path and can quit
                    found_conflict_free_path = True
                    break

                # prioritise conflicts
                conflicts, conflict_costs = self.prioritize_conflicts(
                    conflicts, agents_considered, agent, current_path
                )
                top_priority_conflict = conflicts[0]
                if self.settings["debug_statements"]:
                    print(
                        "\tplanning for agent",
                        agent.id,
                        "found",
                        len(conflicts),
                        "conflicts",
                    )
                conflicting_agent = self.get_agent(
                    top_priority_conflict["conflicting_agent"]
                )
                if conflicting_agent is None:
                    raise Exception(
                        f"Conflict with agent id {top_priority_conflict['conflicting_agent']} but no such agent found."
                    )

                if self.settings["debug_statements"]:
                    print("\t>>Negotiation Started, from Side ", agent.id)
                    print("\t\t Conflict with agent", conflicting_agent.id)

                # solve conflict
                # determine costs
                change_cost_other, alternative_path_other = (
                    conflicting_agent.determine_cost_to_change(
                        to_avoid_path=current_path
                    )
                )
                change_cost_mine, alternative_path_mine = self.determine_my_cost(
                    agent, conflicting_agent, current_path
                )
                if self.settings["debug_statements"]:
                    print(
                        "\t\t Costs other", change_cost_other, "mine", change_cost_mine
                    )

                if alternative_path_other is None:
                    other_resolves_conflict = False
                    if self.settings["debug_statements"]:
                        print(
                            f"Conflict with agent {conflicting_agent.id} but no alternative path found by conflicting agent for them to solve the conflict."
                        )
                else:
                    other_resolves_conflict = self.make_decision(
                        agent,
                        conflicting_agent,
                        change_cost_other,
                        change_cost_mine,
                        negotiation_function,
                        use_agent_params,
                    )

                if self.settings["debug_statements"]:
                    print("\t\t Outcome", other_resolves_conflict)

                if other_resolves_conflict and alternative_path_other is not None:
                    conflicting_agent.change_path_to_satisfy(
                        change_to_path=alternative_path_other
                    )
                else:
                    agents_considered.append(conflicting_agent)

            # Assign final route
            if current_path is not None and found_conflict_free_path:
                current_route = agent.path_planner.convert_path_to_route(current_path)
                agent.route = current_route if current_route else []
                if self.settings["debug_statements"]:
                    print("\tsuccessfully done")
            else:
                # otherwise use token-passing planning (conflict-avoiding)
                agent.plan_route_decentralized_token_passing()
                if self.settings["debug_statements"]:
                    print("\tnegotiations failed")
