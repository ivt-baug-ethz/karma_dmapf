"""Figure 2: distribution of task and service times (box plots) per controller.

Reads ``results/time_distribution/all_{task,service}_times_{CONTROLLER}_{GRID}_{AGENTS}.txt`` for
the four paper controllers in the scenarios 5x5/10, 10x10/30 and 15x15/80 agents (24 files). To
regenerate them, run

    python src/scripts/time_distribution.py

once per controller and scenario, setting ``grid_size`` (base size + 2), ``n_agents`` and
``mapf_control`` in ``simulation_settings`` at the top of the script.
"""

import argparse
import os
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

folder = Path(__file__).resolve().parent.parent / "results" / "time_distribution"
FIGURE_WIDTH = 6.0
FIGURE_HEIGHT = 8.0

controller_file_names = [
    "DECENTRALIZED_TOKEN_PASSING",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA",
]

controller_labels = [
    "Token Passing",
    "Egoistic",
    "Altruistic",
    "Karma",
]

controller_colors = [
    "dodgerblue",
    "olive",
    "green",
    "red",
]


def load_time_values(ftype, controller, grid_size, n_agents):
    file_path = folder / f"{ftype}_{controller}_{grid_size}_{n_agents}.txt"
    with open(file_path, "r") as file:
        values = [float(value) for value in file.read().splitlines() if value.strip()]
    return values


def load_grid_data(grid_size, n_agents):
    return {
        "service_times": [
            load_time_values("all_service_times", controller, grid_size, n_agents)
            for controller in controller_file_names
        ],
        "task_times": [
            load_time_values("all_task_times", controller, grid_size, n_agents)
            for controller in controller_file_names
        ],
    }


def style_boxplot(boxplot, colors, face_mode):
    for patch, color in zip(boxplot["boxes"], colors):
        patch.set_edgecolor(color)
        patch.set_linewidth(1.5)
        if face_mode == "filled":
            patch.set_facecolor(color)
            patch.set_alpha(0.45)
        else:
            patch.set_facecolor("white")
            patch.set_alpha(1.0)
            patch.set_hatch("///")

    for whisker, color in zip(
        boxplot["whiskers"], [color for color in colors for _ in range(2)]
    ):
        whisker.set_color(color)
    for cap, color in zip(
        boxplot["caps"], [color for color in colors for _ in range(2)]
    ):
        cap.set_color(color)
    for median, color in zip(boxplot["medians"], colors):
        median.set_color(color)
        median.set_linewidth(1.5)
    for flier, color in zip(boxplot["fliers"], colors):
        flier.set_markeredgecolor(color)
        # flier.set_markerfacecolor(color)
        flier.set_alpha(0.7)


def plot_paired_boxplots(
    ax, grid_label, grid_data, xlabel=False, show_xtick_labels=True
):
    distribution_positions = [1, 2]
    offsets = [-0.27, -0.09, 0.09, 0.27]
    task_positions = [distribution_positions[0] + offset for offset in offsets]
    service_positions = [distribution_positions[1] + offset for offset in offsets]

    task_boxplot = ax.boxplot(
        grid_data["task_times"],
        positions=task_positions,
        widths=0.14,
        patch_artist=True,
        manage_ticks=False,
    )
    service_boxplot = ax.boxplot(
        grid_data["service_times"],
        positions=service_positions,
        widths=0.14,
        patch_artist=True,
        manage_ticks=False,
    )

    style_boxplot(task_boxplot, controller_colors, "hatched")
    style_boxplot(service_boxplot, controller_colors, "filled")

    ax.set_ylabel(grid_label, fontweight="bold")
    ax.set_xticks(distribution_positions)
    if show_xtick_labels:
        ax.set_xticklabels(["Task Time", "Service Time"])
    else:
        ax.set_xticklabels([])
    # if xlabel:
    #     ax.set_xlabel("Distribution", fontweight="bold")
    ax.margins(x=0.05)

    ax.grid(True, axis="y", alpha=0.2)


def main(
    output_dir: str = str(Path(__file__).resolve().parent), show: bool = True
) -> None:

    if not show or os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        matplotlib.use("Agg")

    data_5 = load_grid_data("5", "10")
    data_10 = load_grid_data("10", "30")
    data_15 = load_grid_data("15", "80")

    fig = plt.figure(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    plot_paired_boxplots(
        plt.subplot(3, 1, 1),
        "5x5 Grid\n(10 agents)",
        data_5,
        show_xtick_labels=False,
    )
    plot_paired_boxplots(
        plt.subplot(3, 1, 2),
        "10x10 Grid\n(30 agents)",
        data_10,
        show_xtick_labels=False,
    )
    plot_paired_boxplots(
        plt.subplot(3, 1, 3), "15x15 Grid\n(80 agents)", data_15, xlabel=True
    )

    legend_handles = [
        Patch(facecolor=color, edgecolor=color, alpha=0.45, label=label)
        for color, label in zip(controller_colors, controller_labels)
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=4,
        fontsize="small",
    )

    plt.tight_layout(rect=(0.0, 0.05, 1.0, 1.0))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Figure_2.png"
    plt.savefig(str(out_path), dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Figure 2")
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(Path(__file__).resolve().parent),
        help="Directory to write the figure to (defaults to script directory)",
    )
    parser.add_argument("--no-show", action="store_true", help="Do not call plt.show()")
    args = parser.parse_args()
    main(output_dir=args.output_dir, show=(not args.no_show))
