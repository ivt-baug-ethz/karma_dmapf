"""Figure 1: efficiency benchmark (completed tasks, A* calls, task and service time vs #agents).

Reads ``results/efficiency_benchmark/summary_{CONTROLLER}_{GRID}.json`` for the four paper
controllers on the 5x5, 10x10 and 15x15 grids (12 files). To regenerate them, run

    python src/scripts/efficiency_benchmark.py

once per controller and grid, setting ``controllers`` to a single controller and ``grid_sizes`` to a
single grid at the top of the script (the output file is named after the last controller in the
list).
"""

import json
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

from paper_style import CONTROLLER_COLORS, CONTROLLER_MARKERS

# Constants / data paths
folder = Path(__file__).resolve().parent.parent / "results" / "efficiency_benchmark"
FIGURE_WIDTH = 6.0 * 2
FIGURE_HEIGHT = 5.0

controllers = [
    ("DECENTRALIZED_TOKEN_PASSING", "Token Passing"),
    ("DECENTRALIZED_NEGOTIATE_EGOISTIC", "Egoistic"),
    ("DECENTRALIZED_NEGOTIATE_ALTRUISTIC", "Altruistic"),
    ("DECENTRALIZED_NEGOTIATE_TRIP_KARMA", "Karma"),
]

grid_sizes = ["5", "10", "15"]
grid_labels = {
    "5": "5x5 Grid",
    "10": "10x10 Grid",
    "15": "15x15 Grid",
}

row_measures = [
    "Completed Tasks",
    "A* Calls",
    "Avg Task Time (incl. Reallocation) (all agents)",
    "Avg Service Time (all agents)",
]

row_labels = [
    "Completion [# Tasks]",
    "Runtime [# A* Calls]",
    "Avg. Task Time [s]",
    "Avg. Service Time [s]",
]

# Preserves the original scaling choices from the previous script.
scale_factors = {
    "5": [10 / 4, 10 / 4, 1, 1],
    "10": [10, 10, 1, 1],
    "15": [10, 10 / 4, 1, 1],
}


def load_data(grid_size, controller, measure, factor=1):
    file_path = folder / f"summary_{controller}_{grid_size}.json"
    with open(file_path, "r") as file:
        data_dict = json.load(file)

    raw_data = data_dict[grid_size][controller]["raw_data"]
    rows = []
    for n_agent, values_by_measure in raw_data.items():
        values = values_by_measure[measure]
        rows.append([n_agent, np.mean(values), np.std(values)])

    df = pd.DataFrame(rows, columns=["n", "mean", "std"])
    df["n"] = pd.to_numeric(df["n"])
    df = df.sort_values("n").reset_index(drop=True)
    df["mean"] = (
        df["mean"].rolling(window=3, center=True, min_periods=1).median() * factor
    )
    df["std"] = (
        df["std"].rolling(window=3, center=True, min_periods=1).median() * factor
    )
    return df


def build_plot_data():
    plot_data = {}
    for grid_size in grid_sizes:
        plot_data[grid_size] = []
        for measure_idx, measure in enumerate(row_measures):
            factor = scale_factors[grid_size][measure_idx]
            controller_dfs = [
                load_data(grid_size, controller_name, measure, factor)
                for controller_name, _ in controllers
            ]
            plot_data[grid_size].append(controller_dfs)
    return plot_data


def plot_subplot(ax, controller_dfs, title=None, ylabel=None, show_legend=False):
    ax.grid(True, alpha=0.2)
    if title is not None:
        ax.set_title(title, fontweight="bold")
    if ylabel is not None:
        ax.set_ylabel(ylabel, fontweight="bold")

    ax.set_xlabel("Density [#Agents]")
    ax.set_xlim(controller_dfs[0]["n"].min(), controller_dfs[0]["n"].max())
    ax.margins(x=0)

    for controller_df, (controller_name, label) in zip(controller_dfs, controllers):
        color = CONTROLLER_COLORS[controller_name]
        ax.plot(
            controller_df["n"],
            controller_df["mean"],
            label=label,
            color=color,
            marker=CONTROLLER_MARKERS[controller_name],
            markersize=4,
        )
        ax.fill_between(
            controller_df["n"],
            controller_df["mean"] - controller_df["std"],
            controller_df["mean"] + controller_df["std"],
            color=color,
            alpha=0.1,
        )

    if show_legend:
        ax.legend(
            fontsize="x-small", loc="upper left", frameon=True, framealpha=0
        )  # transparent box)


def main(
    output_dir: str = str(Path(__file__).resolve().parent), show: bool = True
) -> None:
    if not show or os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        matplotlib.use("Agg")

    plot_data = build_plot_data()
    fig, axes = plt.subplots(3, 4, figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    for row_idx, grid_size in enumerate(grid_sizes):
        for col_idx, controller_dfs in enumerate(plot_data[grid_size]):
            ax = axes[row_idx, col_idx]
            plot_subplot(
                ax,
                controller_dfs,
                title=row_labels[col_idx] if row_idx == 0 else None,
                ylabel=grid_labels[grid_size] if col_idx == 0 else None,
                show_legend=(row_idx == 0 and col_idx == 0),
            )

    plt.subplots_adjust(
        top=0.950, bottom=0.090, left=0.060, right=0.990, hspace=0.400, wspace=0.230
    )

    fig.align_ylabels()

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Figure_1.png"
    fig.savefig(str(out_path), dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Figure 1")
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(Path(__file__).resolve().parent),
        help="Directory to write the figure to (defaults to script directory)",
    )
    parser.add_argument("--no-show", action="store_true", help="Do not call plt.show()")
    args = parser.parse_args()
    main(output_dir=args.output_dir, show=(not args.no_show))
