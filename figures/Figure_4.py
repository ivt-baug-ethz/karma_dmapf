"""Figure 4 (supplementary): trade-off metrics vs karma influence, one figure per metric.

Reads ``results/karma_influence_tradeoffs/summary_grid{GRID}_agents{AGENTS}_T100.json`` for the
scenarios 5x5/10, 10x10/30 and 15x15/80 agents (3 files). To regenerate them, run

    python src/scripts/karma_influence_tradeoffs.py

once per scenario, setting ``GRID_SIZE`` and ``N_AGENTS`` at the top of the script.
"""

from __future__ import annotations

import json
import argparse
import os
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

FOLDER = (
    Path(__file__).resolve().parent.parent / "results" / "karma_influence_tradeoffs"
)

SUMMARY_FILES = [
    "summary_grid5_agents10_T100.json",
    "summary_grid10_agents30_T100.json",
    "summary_grid15_agents80_T100.json",
]

# Metrics to explore as trade-offs against the karma influence parameter.
TRADEOFF_METRICS = [
    "Avg Service Time Increase (%) (all agents)",
    "Completed Tasks",
    "A* Calls",
    "Avg Service Time (all agents)",
    "Std Service Time (all agents)",
]

CONTROLLER_LABELS = {
    "DECENTRALIZED_TOKEN_PASSING": "Token Passing",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "Egoistic",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC": "Altruistic",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "Karma",
}

CONTROLLER_COLORS = {
    "DECENTRALIZED_TOKEN_PASSING": "dodgerblue",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "olive",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC": "green",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "red",
}


def load_summary(summary_filename: str) -> tuple[pd.DataFrame, Dict[str, Any]]:
    base_dir = Path(__file__).resolve().parent.parent
    summary_path = base_dir / FOLDER / summary_filename
    data = json.loads(summary_path.read_text())
    summary_df = pd.DataFrame(data.get("summary", []))
    metadata = data.get("metadata", {})
    return summary_df, metadata


def _plot_metric(
    ax,
    summary_df: pd.DataFrame,
    metadata: Dict[str, Any],
    metric_name: str,
) -> None:
    for controller, label in CONTROLLER_LABELS.items():
        subset = summary_df.loc[
            (summary_df["controller"] == controller)
            & (summary_df["metric"] == metric_name)
        ]
        if subset.empty:
            continue
        subset = subset.sort_values("karma_influence")
        color = CONTROLLER_COLORS.get(controller)
        ax.plot(
            subset["karma_influence"],
            subset["mean"],
            label=label,
            color=color,
            marker="o",
            linewidth=1.5,
            markersize=4,
        )
        if "std" in subset.columns:
            ax.fill_between(
                subset["karma_influence"],
                subset["mean"] - subset["std"],
                subset["mean"] + subset["std"],
                color=color,
                alpha=0.12,
            )

    grid = metadata.get("grid_size_base", "?")
    agents = metadata.get("n_agents", "?")
    ax.set_ylabel(metric_name)
    ax.set_title(
        f"{grid}x{grid} Grid | Agents {agents}", fontsize=10, fontweight="bold"
    )
    ax.grid(True, alpha=0.2)


def plot_tradeoffs(
    summary_dfs: List[pd.DataFrame],
    metadatas: List[Dict[str, Any]],
    output_dir: str = str(Path(__file__).resolve().parent),
    show: bool = True,
) -> None:
    if any(df.empty for df in summary_dfs):
        raise ValueError(
            "One or more summaries are empty; run karma_influence_tradeoffs.py first."
        )

    for metric in TRADEOFF_METRICS:
        plt.style.use("default")
        fig, axes = plt.subplots(len(summary_dfs), 1, figsize=(6.5, 9.0), sharex=True)
        if len(summary_dfs) == 1:
            axes = [axes]

        for ax, summary_df, metadata in zip(axes, summary_dfs, metadatas):
            _plot_metric(ax, summary_df, metadata, metric)

        axes[-1].set_xlabel("Karma Influence")

        # Single legend at bottom (reuse first axis handles)
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

        plt.tight_layout(rect=(0.0, 0.05, 1.0, 1.0))
        safe_metric = metric.replace(" ", "_").replace("%", "perc").replace("/", "-")

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        png_path = out_dir / f"Figure_tradeoff_{safe_metric}.png"
        pdf_path = out_dir / f"Figure_tradeoff_{safe_metric}.pdf"
        fig.savefig(str(png_path), dpi=300)
        fig.savefig(str(pdf_path), dpi=300)

        if show:
            plt.show()
        else:
            plt.close(fig)


def main(
    output_dir: str = str(Path(__file__).resolve().parent), show: bool = True
) -> None:
    if not show or os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        matplotlib.use("Agg")

    summary_dfs: List[pd.DataFrame] = []
    metadatas: List[Dict] = []
    for fname in SUMMARY_FILES:
        df, meta = load_summary(fname)
        summary_dfs.append(df)
        metadatas.append(meta)
    plot_tradeoffs(summary_dfs, metadatas, output_dir=output_dir, show=show)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Figure 4 tradeoffs")
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(Path(__file__).resolve().parent),
        help="Directory to write the figures to (defaults to script directory)",
    )
    parser.add_argument("--no-show", action="store_true", help="Do not call plt.show()")
    args = parser.parse_args()
    main(output_dir=args.output_dir, show=(not args.no_show))
