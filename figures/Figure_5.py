"""Figure 5: task time, task delay, service time and cumulative agent delay per controller.

Reads ``results/delay_evaluation/tasks_grid{GRID}_agents{AGENTS}_T300.json`` for the scenarios
5x5/10 and 10x10/30 agents (2 files). To regenerate them, run

    python src/scripts/delay_evaluation.py

once; it runs both scenarios, the three baselines and Karma (no reset) at every karma influence.

Task time runs from the assignment to the drop-off, and the task delay subtracts the
unobstructed time from the agent's pose at assignment via the pickup to the drop-off. The
cumulative delay is the sum of the task delays of one agent, shown at the end of the run and as
its spread across agents over time.
"""

import argparse
import json
import os
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_hex, to_rgb, to_rgba
from matplotlib.patches import Patch

from paper_style import CONTROLLER_COLORS, CONTROLLER_HATCHES, CONTROLLER_MARKERS

folder = Path(__file__).resolve().parent.parent / "results" / "delay_evaluation"
FIGURE_WIDTH = 15.0
FIGURE_HEIGHT = 6.0
TIME_STEP = 10

scenarios = [("5", "10"), ("10", "30")]

baseline_series = [
    ("DECENTRALIZED_TOKEN_PASSING", None, "Token Passing"),
    ("DECENTRALIZED_NEGOTIATE_EGOISTIC", None, "Egoistic"),
    ("DECENTRALIZED_NEGOTIATE_UTILITARIAN", None, "Utilitarian"),
]
karma_controller = "DECENTRALIZED_NEGOTIATE_KARMA"

columns = ["Task Time", "Task Delay", "Service Time", "Cumulative Delay\n(per agent)"]


def karma_shade(fraction):
    # lighter orange for small karma influences, full Karma orange for the largest
    base = np.array(to_rgb(CONTROLLER_COLORS[karma_controller]))
    return to_hex(1.0 - (1.0 - base) * fraction)


def load_scenario(grid_size, n_agents):
    file_path = folder / f"tasks_grid{grid_size}_agents{n_agents}_T300.json"
    with open(file_path, "r") as file:
        return json.load(file)


def build_series(data):
    influences = data["metadata"]["influences"]
    series = [
        (controller, influence, label, CONTROLLER_COLORS[controller])
        for controller, influence, label in baseline_series
    ]

    for idx, influence in enumerate(influences):
        fraction = 0.5 + 0.5 * idx / max(1, len(influences) - 1)
        series.append(
            (
                karma_controller,
                influence,
                rf"Karma $\tau$={influence}",
                karma_shade(fraction),
            )
        )

    return series


def series_values(data, controller, influence):
    """Per-task times and delays and per-agent cumulative delays over all seeds of one series."""
    task_times, task_delays, service_times, cumulative_delays = [], [], [], []
    spread_over_time = []
    horizon = data["metadata"]["time_simulation_duration"]
    time_points = np.arange(0, horizon + 1, TIME_STEP)

    for run in data["runs"]:
        if run["controller"] != controller or run["karma_influence"] != influence:
            continue

        tasks = np.array(run["tasks"], dtype=float)
        agent_ids, assigned, pickup, completed, min_pickup, min_task = tasks.T
        delays = completed - assigned - min_pickup - min_task
        task_times.extend(completed - assigned)
        task_delays.extend(delays)
        service_times.extend(completed - pickup)

        agents = np.unique(agent_ids)
        cumulative_delays.extend(delays[agent_ids == a].sum() for a in agents)
        spread_over_time.append(
            [
                np.std(
                    [delays[(agent_ids == a) & (completed <= t)].sum() for a in agents]
                )
                for t in time_points
            ]
        )

    return {
        "boxes": [task_times, task_delays, service_times, cumulative_delays],
        "time_points": time_points,
        "spread": np.mean(spread_over_time, axis=0),
    }


def style_boxplot(boxplot, colors, hatches, markers):
    for patch, color, hatch in zip(boxplot["boxes"], colors, hatches):
        patch.set_edgecolor(color)
        patch.set_linewidth(1.2)
        patch.set_hatch(hatch)
        patch.set_facecolor(to_rgba(color, 0.45))
    for whisker, color in zip(
        boxplot["whiskers"], [color for color in colors for _ in range(2)]
    ):
        whisker.set_color(color)
    for cap, color in zip(
        boxplot["caps"], [color for color in colors for _ in range(2)]
    ):
        cap.set_color(color)
    # dark medians stay visible against hatch lines in the box colour
    for median in boxplot["medians"]:
        median.set_color("#222222")
        median.set_linewidth(1.2)
    for flier, color, marker in zip(boxplot["fliers"], colors, markers):
        flier.set_marker(marker)
        flier.set_markersize(3)
        flier.set_markeredgecolor(color)
        flier.set_alpha(0.5)


def plot_scenario(axes, grid_label, data, show_titles):
    series = build_series(data)
    values = [series_values(data, c, i) for c, i, _, _ in series]
    colors = [color for _, _, _, color in series]
    hatches = [CONTROLLER_HATCHES[c] for c, _, _, _ in series]
    markers = [CONTROLLER_MARKERS[c] for c, _, _, _ in series]

    for column, ax in enumerate(axes[:-1]):
        boxplot = ax.boxplot(
            [v["boxes"][column] for v in values],
            widths=0.7,
            patch_artist=True,
        )
        style_boxplot(boxplot, colors, hatches, markers)
        ax.set_xticks([])
        ax.grid(True, axis="y", alpha=0.2)
        if show_titles:
            ax.set_title(columns[column], fontsize="medium")

    ax = axes[-1]
    for v, color, marker in zip(values, colors, markers):
        ax.plot(
            v["time_points"],
            v["spread"],
            color=color,
            marker=marker,
            markevery=5,
            markersize=4,
            linewidth=1.2,
        )
    ax.grid(True, alpha=0.2)
    if show_titles:
        ax.set_title("Std of Cumulative Delay\nacross Agents", fontsize="medium")

    axes[0].set_ylabel(grid_label, fontweight="bold")
    return series


def main(
    output_dir: str = str(Path(__file__).resolve().parent), show: bool = True
) -> None:

    if not show or os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        matplotlib.use("Agg")

    fig, axes = plt.subplots(
        len(scenarios), len(columns) + 1, figsize=(FIGURE_WIDTH, FIGURE_HEIGHT)
    )

    series = []
    for row, (grid_size, n_agents) in enumerate(scenarios):
        series = plot_scenario(
            axes[row],
            f"{grid_size}x{grid_size} Grid\n({n_agents} agents)",
            load_scenario(grid_size, n_agents),
            show_titles=(row == 0),
        )
    axes[-1][-1].set_xlabel("Time [s]")

    legend_handles = [
        Patch(
            facecolor=to_rgba(color, 0.45),
            edgecolor=color,
            hatch=CONTROLLER_HATCHES[controller],
            label=label,
        )
        for controller, _, label, color in series
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=len(legend_handles),
        fontsize="small",
    )

    plt.tight_layout(rect=(0.0, 0.06, 1.0, 1.0))
    fig.align_ylabels()

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Figure_5.png"
    plt.savefig(str(out_path), dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Figure 5")
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(Path(__file__).resolve().parent),
        help="Directory to write the figure to (defaults to script directory)",
    )
    parser.add_argument("--no-show", action="store_true", help="Do not call plt.show()")
    args = parser.parse_args()
    main(output_dir=args.output_dir, show=(not args.no_show))
