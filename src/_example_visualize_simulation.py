"""
POTENTIAL TITLE:
    KARMA MECHANISMS FOR DECENTRALIZED, ORIENTATION-AWARE MAPF

interesting repo: https://github.com/GavinPHR/Multi-Agent-Path-Finding?tab=readme-ov-file
"""

###############################################################################
###### IMPORTS ################################################################
###############################################################################
import os
import numpy as np
from environment import Environment
from planner_path_astar import AStarPathPlanner
from visualization import plot_environment_and_reservation, make_gif

from constants import (
    MAPF_CONTROLLER_CENTRALIZED,
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_ALTRUISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC2,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_ALTRUISTIC2,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
)

###############################################################################
###### PARAMETERS #############################################################
###############################################################################
simulation_settings = {
    "random_seed": 42,
    "grid_size": 20 + 2,  # 15,
    "n_agents": 180,
    # "mapf_control": MAPF_CONTROLLER_CENTRALIZED,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_ALTRUISTIC,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
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
        "initial_karma": 0,
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
# outputs are anchored at the repository root, independent of the working directory
RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"
)
FRAMES_DIR = os.path.join(RESULTS_DIR, "figures_gifs")

environment = Environment(settings=simulation_settings)

# spawn initial agents
for n in range(0, simulation_settings["n_agents"]):
    environment.spawn_agent()

# spawn initial agents
for n in range(0, simulation_settings["n_agents"]):
    environment.spawn_task()

# simulation loop
while environment.time < environment.settings["time_simulation_duration"]:
    print(
        "\n\ntime:",
        environment.time,
        "\t| agents:",
        len(environment.agents),
        "\t| tasks:",
        len(environment.tasks),
    )

    # general update
    environment.time += 1

    # handle agents
    previous_positions = {a.id: list(a.current_position) for a in environment.agents}
    environment.handle_agents()

    # # spawn tasks randomly
    while len(environment.tasks) < len(environment.agents):
        n = len(environment.tasks)
        environment.spawn_task()
        if n == len(environment.tasks):
            break

    # handle tasks
    environment.assign_open_tasks()
    closed = environment.close_finished_tasks()

    # visualize
    os.makedirs(FRAMES_DIR, exist_ok=True)
    plot_environment_and_reservation(
        environment,
        save_filename=os.path.join(FRAMES_DIR, f"x_image_{environment.time:04d}.png"),
    )
    check_violation(environment, previous_positions)

    # report A-STAR Calls
    print("\tA-Star Calls:", AStarPathPlanner.get_counter())
    AStarPathPlanner.reset_counter()

os.makedirs(RESULTS_DIR, exist_ok=True)
make_gif(
    input_pattern=os.path.join(FRAMES_DIR, "x_image_*.png"),
    output_gif=os.path.join(
        RESULTS_DIR, f"animation_{environment.settings['mapf_control']}.gif"
    ),
    duration=0.2,
)
