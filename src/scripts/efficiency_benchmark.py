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
import json
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from src.simulation.metrics import gini, summarize, compute_run_metrics
from src.simulation.environment import Environment
from src.planners.astar import AStarPathPlanner

from src.simulation.constants import (
    MAPF_CONTROLLER_CENTRALIZED,
    MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
)

# outputs are anchored at the repository root, independent of the working directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = os.path.join(ROOT_DIR, "results", "runs", "efficiency_benchmark")
LOG_DIR = os.path.join(ROOT_DIR, "results", "efficiency_benchmark")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


random_seeds = range(41, 51)
grid_sizes = [5]  # , 10, 15, 20]

controllers = [
    # MAPF_CONTROLLER_CENTRALIZED,
    # MAPF_CONTROLLER_DECENTRALIZED_TOKEN_PASSING,
    # MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_EGOISTIC,
    MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_UTILITARIAN,
    # MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_KARMA,
    # MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA,
]

n_agents_map = {
    5: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # max 10
    10: [1, 3, 9, 12, 15, 18, 21, 24, 27, 30],  # max 30
    15: [1, 10, 15, 20, 30, 40, 50, 60, 70, 80],  # max 80
    20: [1, 15, 30, 45, 60, 75, 100, 130, 160, 180],  # max 180
}
results_summary = {}

# Define base simulation settings
base_simulation_settings = {
    "time_horizon_visualization": 10,
    "time_simulation_duration": 100,
    "params_astar": {
        "max_iterations": 1e5,
        "planning_horizon": 50,
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

METRIC_NAMES = [
    "A* Calls",
    "Completed Tasks",
    "Total Task Time (incl. Reallocation) (all agents)",
    "Avg Task Time (incl. Reallocation) (all agents)",
    "Std Task Time (incl. Reallocation) (all agents)",
    "Total Service Time (all agents)",
    "Avg Service Time (all agents)",
    "Std Service Time (all agents)",
    "Avg Service Time Increase (%) (all agents)",
    "Avg Service Time (per agent mean)",
    "Avg Service Increase (%) (per agent mean)",
    "Avg Task Delay (all agents)",
    "Std Task Delay (all agents)",
    "Avg Cumulative Delay (per agent)",
    "Std Cumulative Delay (per agent)",
    "Gini Cumulative Delay (per agent)",
]


def get_markdown_table_str(title, data, algorithms, agents):
    # data[algo][agent] -> (mean, std, median, gini, iqr)

    # 1. Gather all data
    header = ["Algorithm"] + [str(a) for a in agents]
    table_rows = []

    for algo in algorithms:
        row = [algo]
        for agent in agents:
            if agent in data.get(algo, {}):
                mean, std, median, gini_val, iqr = data[algo][agent]
                if title.startswith("Avg") or title.startswith("Std"):
                    val = f"{mean:.2f} ({std:.2f}) | {median:.2f} | {gini_val:.2f} | {iqr:.2f}"
                else:
                    val = f"{mean:.1f} ({std:.1f}) | {median:.1f} | {gini_val:.1f} | {iqr:.1f}"
                row.append(val)
            else:
                row.append("-")
        table_rows.append(row)

    # 2. Determine column widths
    # Initialize with header lengths
    col_widths = [len(h) for h in header]

    # Update with maximum row content lengths
    for row in table_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # 3. Build table string
    lines = []
    lines.append(f"\n{title}")

    # Header
    header_str = (
        "| " + " | ".join(f"{h:<{w}}" for h, w in zip(header, col_widths)) + " |"
    )
    lines.append(header_str)

    # Separator
    separator_str = "| " + " | ".join("-" * w for w in col_widths) + " |"
    lines.append(separator_str)

    # Rows
    for row in table_rows:
        row_str = (
            "| " + " | ".join(f"{cell:<{w}}" for cell, w in zip(row, col_widths)) + " |"
        )
        lines.append(row_str)

    return "\n".join(lines)


def print_markdown_table(title, data, algorithms, agents):
    print(get_markdown_table_str(title, data, algorithms, agents))


def plot_metric(
    metric_name,
    data,
    grid_size,
    agents,
    controllers,
    output_dir=os.path.join(RESULTS_DIR, "figs"),
):
    """
    Plots a given metric for different algorithms using different plot types.
    """
    # create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    # Line plot for mean and std
    _plot_line(metric_name, data, grid_size, agents, controllers, output_dir)
    # Box plot for distribution
    _plot_box(metric_name, data, grid_size, agents, controllers, output_dir)


def _plot_line(
    metric_name,
    data,
    grid_size,
    agents,
    controllers,
    output_dir=os.path.join(RESULTS_DIR, "figs"),
):
    plt.style.use("seaborn-v0_8-paper")
    fig, ax = plt.subplots(figsize=(12, 8))

    for controller in controllers:
        means = [
            data[grid_size][controller][n_agent][metric_name][0]
            for n_agent in agents
            if n_agent in data[grid_size][controller]
        ]
        stds = [
            data[grid_size][controller][n_agent][metric_name][1]
            for n_agent in agents
            if n_agent in data[grid_size][controller]
        ]

        valid_agents = [
            n_agent for n_agent in agents if n_agent in data[grid_size][controller]
        ]

        ax.plot(
            valid_agents, means, marker="o", linestyle="-", label=f"{controller} (Mean)"
        )
        ax.fill_between(
            valid_agents,
            np.array(means) - np.array(stds),
            np.array(means) + np.array(stds),
            alpha=0.2,
        )

    ax.set_xlabel("Number of Agents", fontsize=14)
    ax.set_ylabel(metric_name, fontsize=14)
    ax.set_title(
        f"Mean {metric_name} vs. Number of Agents (Grid Size: {grid_size})",
        fontsize=16,
    )
    ax.legend(fontsize=12)
    ax.tick_params(axis="both", which="major", labelsize=12)
    ax.grid(True)

    filename = f"line_{metric_name.replace(' ', '_').replace('%', 'perc')}_vs_agents_grid_{grid_size}.pdf"
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, format="pdf", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"Saved plot: {filepath}")


def _plot_box(
    metric_name,
    data,
    grid_size,
    agents,
    controllers,
    output_dir=os.path.join(RESULTS_DIR, "figs"),
):
    plt.style.use("seaborn-v0_8-paper")
    fig, ax = plt.subplots(figsize=(16, 8))

    plot_data = []
    for n_agent in agents:
        for controller in controllers:
            if (
                "raw_data" in data[grid_size][controller]
                and n_agent in data[grid_size][controller]["raw_data"]
                and metric_name in data[grid_size][controller]["raw_data"][n_agent]
            ):
                raw_values = data[grid_size][controller]["raw_data"][n_agent][
                    metric_name
                ]
                for val in raw_values:
                    plot_data.append(
                        {"Agents": n_agent, "Controller": controller, "Value": val}
                    )

    if not plot_data:
        print(f"No raw data to plot for {metric_name} (box plot).")
        plt.close(fig)
        return

    df = pd.DataFrame(plot_data)

    sns.boxplot(x="Agents", y="Value", hue="Controller", data=df, ax=ax)

    ax.set_xlabel("Number of Agents", fontsize=14)
    ax.set_ylabel(metric_name, fontsize=14)
    ax.set_title(
        f"Distribution of {metric_name} vs. Number of Agents (Grid Size: {grid_size})",
        fontsize=16,
    )
    ax.legend(fontsize=12)
    ax.tick_params(axis="both", which="major", labelsize=12)
    ax.grid(True)

    filename = f"box_{metric_name.replace(' ', '_').replace('%', 'perc')}_vs_agents_grid_{grid_size}.pdf"
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, format="pdf", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"Saved plot: {filepath}")


# clear summary file
with open(os.path.join(RESULTS_DIR, "summary.txt"), "w") as f:
    f.write("Summary of Results\n")


def run_single_seed(simulation_settings):
    local_settings = simulation_settings.copy()
    local_settings["params_astar"] = simulation_settings["params_astar"].copy()
    local_settings["params_cbs"] = simulation_settings["params_cbs"].copy()
    local_settings["params_karma"] = simulation_settings["params_karma"].copy()

    n_astar_calls = 0
    if local_settings["debug_statements"]:
        print("Starting Experiment", local_settings["random_seed"])

    AStarPathPlanner.reset_counter()
    environment = Environment(settings=local_settings)

    for _ in range(local_settings["n_agents"]):
        environment.spawn_agent()

    for _ in range(local_settings["n_agents"]):
        environment.spawn_task()

    while environment.time < environment.settings["time_simulation_duration"]:
        if local_settings["debug_statements"]:
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

        n_astar_calls += AStarPathPlanner.get_counter()
        AStarPathPlanner.reset_counter()

    return compute_run_metrics(environment.completed_tasks, n_astar_calls)


for grid_size in grid_sizes:
    results_summary[grid_size] = {}
    controllers_run = []
    for controller in controllers:
        if controller not in controllers_run:
            controllers_run.append(controller)
            results_summary[grid_size][controller] = {}

        for n_agent in n_agents_map[grid_size]:
            simulation_settings = base_simulation_settings.copy()
            simulation_settings.update(
                {
                    "random_seed": 42,
                    "grid_size": grid_size + 2,
                    "n_agents": n_agent,
                    "mapf_control": controller,
                }
            )

            metrics_lists = {name: [] for name in METRIC_NAMES}
            seed_jobs = []
            for random_seed in random_seeds:
                seed_settings = simulation_settings.copy()
                seed_settings["random_seed"] = random_seed
                seed_settings["params_astar"] = simulation_settings[
                    "params_astar"
                ].copy()
                seed_settings["params_cbs"] = simulation_settings["params_cbs"].copy()
                seed_settings["params_karma"] = simulation_settings[
                    "params_karma"
                ].copy()
                seed_jobs.append(seed_settings)

            max_workers = min(len(seed_jobs), os.cpu_count() or 1)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                run_metrics_per_seed = list(executor.map(run_single_seed, seed_jobs))

            for run_metrics in run_metrics_per_seed:
                for metric_name, metric_value in run_metrics.items():
                    metrics_lists[metric_name].append(metric_value)

            metrics_summary = {
                metric_name: summarize(values)
                for metric_name, values in metrics_lists.items()
            }

            # Store raw data for box plots
            if "raw_data" not in results_summary[grid_size][controller]:
                results_summary[grid_size][controller]["raw_data"] = {}
            if n_agent not in results_summary[grid_size][controller]["raw_data"]:
                results_summary[grid_size][controller]["raw_data"][n_agent] = {}

            raw_data_storage = results_summary[grid_size][controller]["raw_data"][
                n_agent
            ]
            for metric_name, values in metrics_lists.items():
                raw_data_storage[metric_name] = values

            results_summary[grid_size][controller][n_agent] = metrics_summary

            report_lines = []
            report_lines.append("=====================================================")
            report_lines.append(
                "Experiment Results ["
                + str(simulation_settings["n_agents"])
                + " agents] ["
                + str(simulation_settings["grid_size"] - 2)
                + " grid-size] for algorithm "
                + str(simulation_settings["mapf_control"])
                + " over "
                + str(len(next(iter(metrics_lists.values()), [])))
                + " experiments"
            )
            report_lines.append("=====================================================")

            for metric_name in METRIC_NAMES:
                mean, std, median, gini_val, iqr = metrics_summary[metric_name]
                percent_suffix = "%" if "(%)" in metric_name else ""
                report_lines.append(
                    f"{metric_name:60} mean = {mean:.3f}{percent_suffix} \t std = {std:.3f}{percent_suffix} \t median = {median:.3f}{percent_suffix} \t gini = {gini_val:.3f} \t iqr = {iqr:.3f}{percent_suffix}"
                )

            report_lines.append(
                "=====================================================\n"
            )

            report_str = "\n".join(report_lines)
            print(report_str)

            # Store result in txt file
            # If it is the first agent config, write over, else append
            mode = "w" if n_agent == n_agents_map[grid_size][0] else "a"
            with open(
                os.path.join(RESULTS_DIR, f"results_{controller}_{grid_size}.txt"), mode
            ) as f:
                f.write(report_str + "\n")

    # Print tables for this grid_size
    agents = n_agents_map[grid_size]

    # with open(os.path.join(RESULTS_DIR, "summary.txt"), "a") as f_summary:
    #     f_summary.write(f"\n\n### GRID SIZE {grid_size} SUMMARY ###\n")

    #     # Write simulation settings
    #     f_summary.write("Simulation Settings:\n")
    #     for key, value in base_simulation_settings.items():
    #         f_summary.write(f"  {key}: {value}\n")
    #     f_summary.write(f"  random_seeds_range: {random_seeds}\n")
    #     f_summary.write("\n")

    #     for metric_name in [
    #         "A* Calls",
    #         "Completed Tasks",
    #         "Total Task Time (incl. Reallocation) (all agents)",
    #         "Avg Task Time (incl. Reallocation) (all agents)",
    #         "Std Task Time (incl. Reallocation) (all agents)",
    #         "Total Service Time (all agents)",
    #         "Avg Service Time (all agents)",
    #         "Std Service Time (all agents)",
    #         "Avg Service Time Increase (%) (all agents)",
    #         "Avg Service Time (per agent mean)",
    #         "Avg Service Increase (%) (per agent mean)",
    #     ]:
    #         metric_data = {}
    #         for algo in controllers_run:
    #             metric_data[algo] = {}
    #             for agent in agents:
    #                 if agent in results_summary.get(grid_size, {}).get(algo, {}):
    #                     metric_data[algo][agent] = results_summary[grid_size][algo][
    #                         agent
    #                     ][metric_name]

    #         table_str = get_markdown_table_str(
    #             metric_name, metric_data, controllers_run, agents
    #         )
    #         print(table_str)
    #         f_summary.write(table_str + "\n")

    # Save the results_summary to a JSON file for plotting
    # Convert keys to strings for JSON compatibility
    results_summary_str_keys = {}
    for k, v in results_summary.items():
        grid_size_key = str(k)
        results_summary_str_keys[grid_size_key] = {}
        for controller, controller_data in v.items():
            controller_key = str(controller)
            results_summary_str_keys[grid_size_key][controller_key] = {}
            for n_agent, agent_data in controller_data.items():
                agent_key = str(n_agent)
                results_summary_str_keys[grid_size_key][controller_key][
                    agent_key
                ] = agent_data

    with open(
        os.path.join(LOG_DIR, f"summary_{controllers[-1]}_{grid_size}.json"), "w"
    ) as f_json:
        # Custom encoder to handle numpy arrays
        class NumpyEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, np.ndarray):
                    return o.tolist()
                if isinstance(o, np.integer):
                    return int(o)
                if isinstance(o, np.floating):
                    return float(o)
                return json.JSONEncoder.default(self, o)

        json.dump(results_summary_str_keys, f_json, indent=4, cls=NumpyEncoder)

    # # Plotting results
    # for grid_size_str, grid_data in results_summary_str_keys.items():
    #     grid_size = int(grid_size_str)
    #     controllers = [c for c in grid_data.keys() if c != "raw_data"]

    #     # Determine the union of agents for this grid size
    #     all_agents = set()
    #     for controller in controllers:
    #         all_agents.update(grid_data[controller].keys())

    #     # Convert agent keys from string to int and sort
    #     agents = sorted([int(a) for a in all_agents if a.isdigit()])

    #     # Get all metric names from the first available data point
    #     metric_names = []
    #     if controllers and agents:
    #         first_controller = controllers[0]
    #         first_agent_str = str(agents[0])
    #         if first_agent_str in grid_data[first_controller]:
    #             metric_names = [
    #                 k
    #                 for k in grid_data[first_controller][first_agent_str].keys()
    #                 if k != "raw_data"
    #             ]

    #     if not metric_names:
    #         print(f"No metrics found for grid size {grid_size}. Skipping.")
    #         continue

    #     for metric_name in metric_names:
    #         plot_metric(
    #             metric_name,
    #             results_summary,
    #             grid_size,
    #             agents,
    #             controllers,
    #         )
