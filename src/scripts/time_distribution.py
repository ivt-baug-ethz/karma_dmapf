"""
POTENTIAL TITLE:
    KARMA MECHANISMS FOR DECENTRALIZED, ORIENTATION-AWARE MAPF

interesting repo: https://github.com/GavinPHR/Multi-Agent-Path-Finding?tab=readme-ov-file
"""

###############################################################################
###### IMPORTS ################################################################
###############################################################################
import numpy as np
import os
from src.simulation.environment import Environment
from src.planners.astar import AStarPathPlanner
from src.simulation.visualization import plot_environment_and_reservation, make_gif

from src.simulation.constants import (
    MAPF_CONTROLLER_CENTRALIZED,
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
)

###############################################################################
###### PARAMETERS #############################################################
###############################################################################

random_seeds = [n for n in range(41, 51)]

# outputs are anchored at the repository root, independent of the working directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(ROOT_DIR, "results", "time_distribution")
os.makedirs(LOG_DIR, exist_ok=True)

simulation_settings = {
    "random_seed": 42,
    "grid_size": 10 + 2,  # 15,
    "n_agents": 30,
    # "mapf_control": MAPF_CONTROLLER_CENTRALIZED,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
    "time_horizon_visualization": 10,
    "time_simulation_duration": 100,
    "params_astar": {
        "max_iterations": 1e5,
        "planning_horizon": int(20 * 20),
        "planning_horizon_buffer": 20,
    },
    "params_cbs": {
        "max_iterations": 5000,
        "MAX_IDLE_TIME_CONSIDERED": 20,
        "PLANNING_HORIZON": 100,
    },
    "params_karma": {
        "initial_karma": 20,
        "delta_threshold": 0,
        "karma_influence": 0.5,
    },
    "debug_statements": False,
}


def check_violation(environment, previous_positions=None):
    # vertex conflicts
    for i, agent_a in enumerate(environment.agents):
        for agent_b in environment.agents[i + 1 :]:
            if tuple(agent_a.current_position) == tuple(agent_b.current_position):
                raise Exception(
                    f"[{environment.time}] Vertex conflict: agents {agent_a.id} and {agent_b.id} "
                    f"at {agent_a.current_position}"
                )

    # edge conflicts
    if previous_positions is not None:
        for i, agent_a in enumerate(environment.agents):
            for agent_b in environment.agents[i + 1 :]:
                prev_a = tuple(previous_positions[agent_a.id])
                prev_b = tuple(previous_positions[agent_b.id])
                curr_a = tuple(agent_a.current_position)
                curr_b = tuple(agent_b.current_position)

                if prev_a == curr_b and prev_b == curr_a and curr_a != curr_b:
                    raise Exception(
                        f"[{environment.time}] Edge conflict: agents {agent_a.id} and {agent_b.id} "
                        f"swapped {prev_a} <-> {prev_b}"
                    )


###############################################################################
###### MAIN ###################################################################
###############################################################################
def run_single_seed(seed):
    seed_settings = simulation_settings.copy()
    seed_settings["random_seed"] = seed
    seed_settings["params_astar"] = simulation_settings["params_astar"].copy()
    seed_settings["params_cbs"] = simulation_settings["params_cbs"].copy()
    seed_settings["params_karma"] = simulation_settings["params_karma"].copy()

    environment = Environment(settings=seed_settings)

    for _ in range(seed_settings["n_agents"]):
        environment.spawn_agent()

    for _ in range(seed_settings["n_agents"]):
        environment.spawn_task()

    while environment.time < environment.settings["time_simulation_duration"]:
        print(
            "\nseed:",
            seed,
            "\ttime:",
            environment.time,
            "\t| agents:",
            len(environment.agents),
            "\t| tasks:",
            len(environment.tasks),
        )

        # advance the simulation by one time step
        # (includes route execution, task assignment, and route planning)
        environment.step()

        # Uncomment for conflict debugging if needed.
        # check_violation(environment, previous_positions)

        print("\tA-Star Calls:", AStarPathPlanner.get_counter())
        AStarPathPlanner.reset_counter()

    seed_task_times = []
    seed_service_times = []
    for agent in environment.completed_tasks:
        for task in environment.completed_tasks[agent]:
            if task.completed_time is not None and task.assigned_time is not None:
                task_time = task.completed_time - task.assigned_time
                seed_task_times.append(task_time)
                if task.pickup_time is not None:
                    service_time = task.completed_time - task.pickup_time
                    seed_service_times.append(service_time)

    return seed_task_times, seed_service_times


all_task_times = []
all_service_times = []

for seed in random_seeds:
    seed_task_times, seed_service_times = run_single_seed(seed)
    all_task_times.extend(seed_task_times)
    all_service_times.extend(seed_service_times)

task_times_path = os.path.join(
    LOG_DIR,
    f"all_task_times_{simulation_settings['mapf_control']}_"
    f"{simulation_settings['grid_size']-2}_{simulation_settings['n_agents']}.txt",
)
with open(task_times_path, "w+") as f:
    for time in all_task_times:
        f.write(str(time))
        f.write("\n")

service_times_path = os.path.join(
    LOG_DIR,
    f"all_service_times_{simulation_settings['mapf_control']}_"
    f"{simulation_settings['grid_size']-2}_{simulation_settings['n_agents']}.txt",
)
with open(service_times_path, "w+") as f:
    for time in all_service_times:
        f.write(str(time))
        f.write("\n")

print(f"\nStored {len(all_task_times)} task times in {task_times_path}")
print(f"Stored {len(all_service_times)} service times in {service_times_path}")
