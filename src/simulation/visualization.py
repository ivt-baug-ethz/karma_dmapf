import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from matplotlib import cm
from typing import List, Any

from src.simulation.constants import (
    SQUARE_SYMBOL_OCCUPIED,
    AGENT_STATUS_CARRY,
    AGENT_STATUS_PICKUP,
    AGENT_STATUS_IDLE,
    AGENT_STATUS_DROPOFF,
)
from src.simulation.constants import (
    AGENT_ORIENTATION_SOUTH,
    AGENT_ORIENTATION_NORTH,
    AGENT_ORIENTATION_EAST,
)
import imageio.v2 as imageio
import glob
from src.simulation.geometry import GridTools


def plot_grid(environment, save_filename=None):
    fig, ax = plt.subplots(figsize=(10, 10))

    # Set white background
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Hide axes
    ax.set_xlim(-0.5, environment.grid.grid_size - 0.5)
    ax.set_ylim(-0.5, environment.grid.grid_size - 0.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # Draw light gray grid squares (slightly smaller than full size)
    grid_size = environment.grid.grid_size
    for i in range(grid_size):
        for j in range(grid_size):
            # Color based on occupancy
            is_occupied = (
                environment.grid.occupancy_grid[i, j] == SQUARE_SYMBOL_OCCUPIED
            )
            facecolor = (
                "#d0d0d0" if is_occupied else "#f0f0f0"
            )  # darker gray vs light gray
            # 0.85 size creates white lines between squares
            rect = patches.Rectangle(
                (i - 0.425, j - 0.425),
                0.85,
                0.85,
                linewidth=0.5,
                edgecolor="white",
                facecolor=facecolor,
            )
            ax.add_patch(rect)
            ax.text(
                i,
                j - 0.5,
                f"({i},{j})",
                ha="center",
                va="center",
                fontsize=6,
                fontweight="bold",
                color="darkgray",
            )

    # Plot CONNECTIONS between agents and their assigned tasks (blue dashed lines)
    task_size = 0.2
    for agent in environment.agents:
        if agent.assigned_task is not None:  # Agent has a task assigned
            if agent.assigned_task:
                # Draw red arrow from agent to task.from_position
                if agent.status == AGENT_STATUS_PICKUP:
                    ax.annotate(
                        "",
                        xy=agent.assigned_task.from_position,
                        xytext=agent.current_position,
                        arrowprops=dict(arrowstyle="->", color="red", lw=2, alpha=0.5),
                    )
                # Draw blue arrow from task.from_position to task.to_position
                ax.annotate(
                    "",
                    xy=agent.assigned_task.to_position,
                    xytext=agent.assigned_task.current_position,
                    arrowprops=dict(arrowstyle="->", color="blue", lw=2, alpha=0.5),
                )

                # Draw blue rectangle at target position (to_position) with alpha=0.3
                target_rect = patches.Rectangle(
                    (
                        agent.assigned_task.to_position[0] - task_size / 2,
                        agent.assigned_task.to_position[1] - task_size / 2,
                    ),
                    task_size,
                    task_size,
                    linewidth=2,
                    edgecolor="blue",
                    facecolor="blue",
                    alpha=0.3,
                )
                ax.add_patch(target_rect)

    # Plot tasks (small filled black squares)
    for task in environment.tasks:
        color = "black"
        if task.assigned_agent:
            if task.assigned_agent.status == AGENT_STATUS_CARRY:
                color = "cyan"
        rect = patches.Rectangle(
            (
                task.current_position[0] - task_size / 2,
                task.current_position[1] - task_size / 2,
            ),
            task_size,
            task_size,
            linewidth=1,
            edgecolor=color,
            facecolor=color,
        )
        ax.add_patch(rect)

    # Plot agents (circles with orientation lines)
    for agent in environment.agents:
        # Circle color based on status
        color_map = {
            AGENT_STATUS_IDLE: "darkgray",
            AGENT_STATUS_PICKUP: "red",
            AGENT_STATUS_CARRY: "orange",
            AGENT_STATUS_DROPOFF: "green",
        }
        circle_color = color_map.get(agent.status, "darkgray")

        # Agent circle (unfilled)
        circle = patches.Circle(
            agent.current_position,
            0.3,
            linewidth=2,
            edgecolor=circle_color,
            facecolor="none",
        )
        ax.add_patch(circle)

        # Orientation line (only for non-idle agents)
        center_x, center_y = agent.current_position
        length = 0.3
        if agent.current_orientation == AGENT_ORIENTATION_NORTH:
            dx, dy = 0, length
        elif agent.current_orientation == AGENT_ORIENTATION_EAST:
            dx, dy = length, 0
        elif agent.current_orientation == AGENT_ORIENTATION_SOUTH:
            dx, dy = 0, -length
        else:  # WEST
            dx, dy = -length, 0

        line = Line2D(
            [center_x + dx / 2, center_x + dx],
            [center_y + dy / 2, center_y + dy],
            color=circle_color,
            linewidth=3,
        )
        ax.add_line(line)

    plt.title(
        f"t = {environment.time:04d}  |  agents = {len(environment.agents)}  |  tasks = {len(environment.tasks):02d}",
        fontsize=16,
        pad=20,
    )

    if save_filename:
        plt.savefig(save_filename, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)  # <- this prevents the window from opening
    else:
        plt.show()


def draw_reservation_table(reservation_table, save_filename=None):
    rt = reservation_table.reservation_table  # shape (T, X, Y)
    t_idx, x_idx, y_idx = np.where(rt > 0)
    agent_ids = rt[t_idx, x_idx, y_idx]

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")

    # get unique agents
    unique_agents = np.unique(agent_ids)
    colors = cm.get_cmap("tab20", len(unique_agents))  # colormap for agents

    for i, agent in enumerate(unique_agents):
        mask = agent_ids == agent
        t = t_idx[mask]
        x = x_idx[mask]
        y = y_idx[mask]

        # sort by time to connect lines
        order = np.argsort(t)
        t = t[order]
        x = x[order]
        y = y[order]

        ax.plot(
            x,
            y,
            t,
            marker="o",
            markersize=4,
            linewidth=2,
            color=colors(i),
            label=f"agent {int(agent)}",
        )

    # axis labels
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Time", rotation=90)

    # set equal aspect
    ax.set_xlim(-0.5, rt.shape[1] - 0.5)
    ax.set_ylim(-0.5, rt.shape[2] - 0.5)
    ax.set_zlim(-0.5, rt.shape[0] - 0.5)
    ax.set_box_aspect((1, 1, 1))  # cube aspect

    ax.legend(loc="upper left", fontsize=8)

    if save_filename:
        plt.savefig(save_filename, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def plot_environment_and_reservation(environment, save_filename=None):
    """
    Plots side by side:
    - Left: 2D grid with agents and tasks
    - Right: 3D reservation table
    """
    import matplotlib

    matplotlib.use("Agg")

    fig = plt.figure(figsize=(20, 10))  # wider for side-by-side

    # -------------------- LEFT: 2D grid --------------------
    ax1 = fig.add_subplot(1, 2, 1)
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("white")
    ax1.set_xlim(-0.5, environment.grid.grid_size - 0.5)
    ax1.set_ylim(-0.5, environment.grid.grid_size - 0.5)
    ax1.set_aspect("equal")
    ax1.axis("off")

    grid_size = environment.grid.grid_size
    for i in range(grid_size):
        for j in range(grid_size):
            is_occupied = (
                environment.grid.occupancy_grid[i, j] == SQUARE_SYMBOL_OCCUPIED
            )
            facecolor = "#d0d0d0" if is_occupied else "#f0f0f0"
            rect = patches.Rectangle(
                (i - 0.425, j - 0.425),
                0.85,
                0.85,
                linewidth=0.5,
                edgecolor="white",
                facecolor=facecolor,
            )
            ax1.add_patch(rect)
            ax1.text(
                i,
                j - 0.5,
                f"({i},{j})",
                ha="center",
                va="center",
                fontsize=6,
                fontweight="bold",
                color="darkgray",
            )

    task_size = 0.2
    for agent in environment.agents:
        if agent.assigned_task:
            if agent.status == AGENT_STATUS_PICKUP:
                ax1.annotate(
                    "",
                    xy=agent.assigned_task.from_position,
                    xytext=agent.current_position,
                    arrowprops=dict(arrowstyle="->", color="red", lw=2, alpha=0.5),
                )
            ax1.annotate(
                "",
                xy=agent.assigned_task.to_position,
                xytext=agent.assigned_task.current_position,
                arrowprops=dict(arrowstyle="->", color="blue", lw=2, alpha=0.5),
            )
            # target rectangle
            rect = patches.Rectangle(
                (
                    agent.assigned_task.to_position[0] - task_size / 2,
                    agent.assigned_task.to_position[1] - task_size / 2,
                ),
                task_size,
                task_size,
                linewidth=2,
                edgecolor="blue",
                facecolor="blue",
                alpha=0.3,
            )
            ax1.add_patch(rect)

    for task in environment.tasks:
        color = "black"
        if task.assigned_agent and task.assigned_agent.status == AGENT_STATUS_CARRY:
            color = "cyan"
        rect = patches.Rectangle(
            (
                task.current_position[0] - task_size / 2,
                task.current_position[1] - task_size / 2,
            ),
            task_size,
            task_size,
            linewidth=1,
            edgecolor=color,
            facecolor=color,
        )
        ax1.add_patch(rect)

    for agent in environment.agents:
        color_map = {
            AGENT_STATUS_IDLE: "darkgray",
            AGENT_STATUS_PICKUP: "red",
            AGENT_STATUS_CARRY: "orange",
            AGENT_STATUS_DROPOFF: "green",
        }
        circle_color = color_map.get(agent.status, "darkgray")
        circle = patches.Circle(
            agent.current_position,
            0.3,
            linewidth=2,
            edgecolor=circle_color,
            facecolor="none",
        )
        ax1.add_patch(circle)
        # orientation line
        cx, cy = agent.current_position
        length = 0.3
        if agent.current_orientation == AGENT_ORIENTATION_NORTH:
            dx, dy = 0, length
        elif agent.current_orientation == AGENT_ORIENTATION_EAST:
            dx, dy = length, 0
        elif agent.current_orientation == AGENT_ORIENTATION_SOUTH:
            dx, dy = 0, -length
        else:
            dx, dy = -length, 0
        line = Line2D(
            [cx + dx / 2, cx + dx],
            [cy + dy / 2, cy + dy],
            color=circle_color,
            linewidth=3,
        )
        ax1.add_line(line)

    ax1.set_title(
        f"Time={environment.time:04d} | Agents={len(environment.agents)} | Tasks={len(environment.tasks):02d}",
        fontsize=14,
    )

    # -------------------- RIGHT: 3D reservation table --------------------
    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    rt = GridTools.create_3D_reservation_grid(
        environment, environment.settings["time_horizon_visualization"]
    )
    occupied_mask = np.not_equal(rt, -1)
    t_idx, x_idx, y_idx = np.where(occupied_mask)
    agent_ids = rt[t_idx, x_idx, y_idx]
    unique_agents = np.unique(agent_ids)
    colors = cm.get_cmap("tab20", len(unique_agents))

    for i, agent in enumerate(unique_agents):
        mask = agent_ids == agent
        t = t_idx[mask]
        x = x_idx[mask]
        y = y_idx[mask]
        order = np.argsort(t)
        ax2.plot(
            x[order],
            y[order],
            t[order],
            marker="o",
            markersize=4,
            linewidth=2,
            color=colors(i),
            label=f"agent {int(agent)}",
        )

    ax2.set_xlabel("X")
    ax2.set_ylabel("Y")
    ax2.set_zlabel("Time", rotation=90)
    ax2.set_xlim(-0.5, rt.shape[1] - 0.5)
    ax2.set_ylim(-0.5, rt.shape[2] - 0.5)
    ax2.set_zlim(-0.5, rt.shape[0] - 0.5)
    ax2.set_box_aspect((1, 1, 1))
    if len(unique_agents) < 30:
        ax2.legend(loc="upper left", fontsize=8)

    ax2.set_title("Braid Diagram (Reservation Table)", fontsize=14)

    plt.tight_layout()
    if save_filename:
        plt.savefig(save_filename, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def make_gif(
    input_pattern: str,
    output_gif: str,
    duration: float = 0.2,
) -> None:
    # Collect and sort frames
    frames: List[str] = sorted(glob.glob(input_pattern))
    images: List[Any] = [imageio.imread(f) for f in frames]
    imageio.mimsave(output_gif, images, duration=duration)
