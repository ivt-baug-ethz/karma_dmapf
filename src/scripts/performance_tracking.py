"""
POTENTIAL TITLE:
    KARMA MECHANISMS FOR DECENTRALIZED, ORIENTATION-AWARE MAPF

interesting repo: https://github.com/GavinPHR/Multi-Agent-Path-Finding?tab=readme-ov-file
"""

###############################################################################
###### IMPORTS ################################################################
###############################################################################
import numpy as np
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
simulation_settings = {
    "random_seed": 42,
    "grid_size": 14,
    "n_agents": 10,
    # "mapf_control": MAPF_CONTROLLER_CENTRALIZED,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    # "mapf_control": MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
    "time_horizon_visualization": 10,
    "time_simulation_duration": 1000,
    "params_astar": {
        "max_iterations": 5000,
        "planning_horizon": int(20 * 20),
        "planning_horizon_buffer": 20,
    },
    "params_cbs": {
        "max_iterations": 5000,
        "MAX_IDLE_TIME_CONSIDERED": 5,
        "PLANNING_HORIZON": 100,
    },
    "params_karma": {
        "initial_karma": 20,
        "delta_threshold": 0,
        "karma_influence": 0.5,
    },
    "debug_statements": False,
}


###############################################################################
###### MAIN ###################################################################
###############################################################################
astar_calls_list = []
n_completed_tasks_list = []
n_total_cost_list = []
n_average_cost_list = []
n_distribution_list = []

for random_seed in range(41, 51):
    simulation_settings["random_seed"] = random_seed
    n_astar_calls = 0
    print("Starting Experiment", random_seed)
    environment = Environment(settings=simulation_settings)

    # spawn initial agents
    for n in range(0, simulation_settings["n_agents"]):
        environment.spawn_agent()

    # spawn initial tasks
    for n in range(0, simulation_settings["n_agents"]):
        environment.spawn_task()

    # simulation loop
    while environment.time < environment.settings["time_simulation_duration"]:
        print(
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

        # report A-STAR Calls
        n_astar_calls += AStarPathPlanner.get_counter()
        AStarPathPlanner.reset_counter()

    # evaluation
    all_completed_tasks = [
        task for task_list in environment.completed_tasks.values() for task in task_list
    ]
    task_completion_times = [
        task.completed_time - task.spawned_time
        for task in all_completed_tasks
        if task.completed_time is not None
    ]
    n_completed_tasks = len(task_completion_times)
    n_total_cost = np.sum(task_completion_times)
    n_average_cost = np.mean(task_completion_times)
    n_distribution = np.std(task_completion_times)
    # store metrics
    astar_calls_list.append(n_astar_calls)
    n_completed_tasks_list.append(n_completed_tasks)
    n_total_cost_list.append(n_total_cost)
    n_average_cost_list.append(n_average_cost)
    n_distribution_list.append(n_distribution)


def summarize(x):
    x = np.array(x, dtype=float)
    return x.mean(), x.std(ddof=0)  # population std; use ddof=1 for sample std


avg_astar, std_astar = summarize(astar_calls_list)
avg_completed, std_completed = summarize(n_completed_tasks_list)
avg_total_cost, std_total_cost = summarize(n_total_cost_list)
avg_avg_cost, std_avg_cost = summarize(n_average_cost_list)
avg_distribution, std_distribution = summarize(n_distribution_list)

print("=====================================================")
print(
    "Experiment Results for algorithm",
    simulation_settings["mapf_control"],
    "over",
    len(astar_calls_list),
    "experiments",
)
print("=====================================================")
print("A* calls:        mean = {:.3f} \t std = {:.3f}".format(avg_astar, std_astar))
print(
    "Completed tasks: mean = {:.3f} \t std = {:.3f}".format(
        avg_completed, std_completed
    )
)
print(
    "Total cost:      mean = {:.3f} \t std = {:.3f}".format(
        avg_total_cost, std_total_cost
    )
)
print(
    "Avg cost (all):  mean = {:.3f} \t std = {:.3f}".format(avg_avg_cost, std_avg_cost)
)
print(
    "Distribution:    mean = {:.3f} \t std = {:.3f}".format(
        avg_distribution, std_distribution
    )
)
print("=====================================================")

"""
=====================================================
Experiment Results for algorithm DECENTRALIZED_TOKEN_PASSING over 10 experiments
=====================================================
A* calls:        mean = 77801.400 	 std = 3732.673
Completed tasks: mean = 496.400 	 std = 6.312
Total cost:      mean = 9231.800 	 std = 18.686
Avg cost:        mean = 18.601 	 std = 0.266
Distribution:    mean = 5.775 	 std = 0.168
=====================================================

=====================================================
Experiment Results for algorithm DECENTRALIZED_NEGOTIATE_EGOISTIC over 10 experiments
=====================================================
A* calls:        mean = 187876.300 	 std = 14002.736
Completed tasks: mean = 507.200 	 std = 6.954
Total cost:      mean = 9219.200 	 std = 12.929
Avg cost:        mean = 18.180 	 std = 0.248
Distribution:    mean = 5.593 	 std = 0.159
=====================================================

=====================================================
Experiment Results for algorithm DECENTRALIZED_NEGOTIATE_UTILITARIAN over 10 experiments
=====================================================
A* calls:        mean = 168357.700 	 std = 10569.894
Completed tasks: mean = 507.700 	 std = 7.669
Total cost:      mean = 9213.300 	 std = 16.710
Avg cost:        mean = 18.151 	 std = 0.273
Distribution:    mean = 5.612 	 std = 0.174
=====================================================

=====================================================
Experiment Results for algorithm DECENTRALIZED_NEGOTIATE_KARMA over 10 experiments
=====================================================
A* calls:        mean = 181295.800 	 std = 15864.907
Completed tasks: mean = 503.900 	 std = 7.595
Total cost:      mean = 9226.900 	 std = 33.533
Avg cost:        mean = 18.315 	 std = 0.301
Distribution:    mean = 5.606 	 std = 0.245
=====================================================
"""
