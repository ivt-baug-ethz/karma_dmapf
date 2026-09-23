"""Figure 3: service time increase vs karma influence for the four paper controllers.

Reads ``results/karma_influence/summary_grid{GRID}_agents{AGENTS}_T100.json`` for the scenarios
5x5/10, 10x10/30 and 15x15/80 agents (3 files). To regenerate them, run

    python src/scripts/karma_influence.py

once per scenario, setting ``GRID_SIZE`` and ``N_AGENTS`` at the top of the script.
"""

from __future__ import annotations

import os
import json
import argparse
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path

import pandas as pd

folder = Path(__file__).resolve().parent.parent / "results" / "karma_influence"
FIGURE_WIDTH = 6.0 * 2
FIGURE_HEIGHT = 3.0

METRIC_NAME = "Avg Service Time Increase (%) (all agents)"
SUMMARY_FILES = [
    "summary_grid5_agents10_T100.json",
    "summary_grid10_agents30_T100.json",
    "summary_grid15_agents80_T100.json",
]

CONTROLLER_LABELS = {
    "DECENTRALIZED_TOKEN_PASSING": "Token Passing",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "Egoistic",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC": "Altruistic",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "Karma",
}

# Match Figure_2 palette
CONTROLLER_COLORS = {
    "DECENTRALIZED_TOKEN_PASSING": "dodgerblue",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "olive",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC": "green",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "red",
}


def load_summary(summary_filename: str) -> tuple[pd.DataFrame, dict]:
    summary_path = folder / summary_filename
    data = json.loads(summary_path.read_text())
    summary_df = pd.DataFrame(data.get("summary", []))
    metadata = data.get("metadata", {})
    return summary_df, metadata


def plot_influences(
    summary_dfs: list[pd.DataFrame],
    metadatas: list[dict],
    output_dir: str = str(Path(__file__).resolve().parent),
    show: bool = True,
) -> None:

    if any(df.empty for df in summary_dfs):
        raise ValueError(
            "One or more summaries are empty; run the analysis script first."
        )

    plt.style.use("default")
    fig, axes = plt.subplots(
        1,
        len(summary_dfs),
        figsize=(FIGURE_WIDTH, FIGURE_HEIGHT),
        sharex=True,
        sharey=False,
    )
    if len(summary_dfs) == 1:
        axes = [axes]

    for idx, (ax, summary_df, metadata) in enumerate(zip(axes, summary_dfs, metadatas)):
        for controller, label in CONTROLLER_LABELS.items():
            subset = summary_df.loc[
                (summary_df["controller"] == controller)
                & (summary_df["metric"] == METRIC_NAME)
            ]
            if subset.empty:
                continue
            subset = subset.sort_values("karma_influence")
            color = CONTROLLER_COLORS.get(controller, None)
            ax.plot(
                subset["karma_influence"],
                subset["mean"],
                label=label,
                color=color,
                # marker="o",
                # linewidth=1.5,
                # markersize=4,
            )
            if "std" in subset.columns:
                ax.fill_between(
                    subset["karma_influence"],
                    subset["mean"] - subset["std"],
                    subset["mean"] + subset["std"],
                    color=color,
                    alpha=0.1,
                )

        grid = metadata.get("grid_size_base", "?")
        agents = metadata.get("n_agents", "?")
        if idx == 0:
            ax.set_ylabel("Service Time Increase [%]")
        else:
            ax.set_ylabel("")
        ax.tick_params(axis="y", which="both", labelleft=True)
        ax.set_title(
            f"{grid}x{grid} Grid\n(Agents {agents})", fontsize=10, fontweight="bold"
        )
        ax.grid(True, alpha=0.2)

    for ax in axes:
        ax.set_xlabel(r"$\tau$ ")

    # Single legend at bottom
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=4,
        fontsize="small",
        frameon=True,
        edgecolor="lightgray",
        facecolor="white",
        framealpha=1.0,
    )

    plt.tight_layout()
    fig.subplots_adjust(top=0.867, bottom=0.249, wspace=0.120)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Figure_3.png"
    fig.savefig(str(out_path), dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)


def main(
    output_dir: str = str(Path(__file__).resolve().parent), show: bool = True
) -> None:
    if not show or os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        matplotlib.use("Agg")

    summary_dfs: list[pd.DataFrame] = []
    metadatas: list[dict] = []
    for fname in SUMMARY_FILES:
        df, meta = load_summary(fname)
        summary_dfs.append(df)
        metadatas.append(meta)
    plot_influences(summary_dfs, metadatas, output_dir=output_dir, show=show)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Figure 3")
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(Path(__file__).resolve().parent),
        help="Directory to write the figure to (defaults to script directory)",
    )
    parser.add_argument("--no-show", action="store_true", help="Do not call plt.show()")
    args = parser.parse_args()
    main(output_dir=args.output_dir, show=(not args.no_show))
