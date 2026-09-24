# Simulation core

## Step loop (duplicated in every script, no shared runner)

```
env = Environment(settings); spawn_agent() × n_agents; spawn_task() × n_agents
while env.time < T:
    env.time += 1
    env.handle_agents()                 # execute one route step, then plan (per controller)
    env.close_finished_tasks()          # release delivering agents before assignment
    top up: spawn_task() until len(tasks) == len(agents) or a spawn fails
    env.assign_open_tasks()
    n_astar += AStarPathPlanner.get_counter(); AStarPathPlanner.reset_counter()
```

`performance_tracking` spawns at most one task per step (`if`, not `while`);
every other script tops up. A change to the loop must be repeated in each script
(`mem:open_issues`). Releasing before assigning lets a delivering agent get a new task in the same
step. With the opposite order, every delivery cost at least one idle step: idle time was about 12%
of agent-steps, now it is about 6%. Most of the remaining idle time comes from the assignment
reserving open tasks for CARRY agents. A task backlog (#tasks > #agents) would remove it, but it
was only evaluated (`TO_FIX.md`).

## Settings dict (`Environment.settings`)

Keys: `random_seed`, `grid_size` (base + 2), `n_agents`, `mapf_control`,
`time_simulation_duration`, `time_horizon_visualization` (unused by the sim), `debug_statements`,
`params_astar {max_iterations, planning_horizon, planning_horizon_buffer}`,
`params_cbs {max_iterations, MAX_IDLE_TIME_CONSIDERED, PLANNING_HORIZON}`,
`params_karma {initial_karma, delta_threshold, karma_influence}`. Scripts copy nested dicts
(`copy.deepcopy` or per-key `.copy()`) before mutating; keep doing that because settings are shared
across seed jobs.

## Agents and tasks

- Status: `IDLE` (no task), `PICKUP` (driving to `from_position`), `CARRY` (driving to
  `to_position`). `DROPOFF` exists in constants but is never set.
- Orientation N=0, E=1, S=2, W=3. Route actions: `N/E/S/W` = move forward (only valid if facing that
  way), `C`/`A` = rotate clockwise/anticlockwise, `T` = wait. Each action is one time step.
- `assign_open_tasks` considers idle **and** CARRY agents (available soon), but only idle agents get
  the task this step. Cost = arrival time − 0.2·wait time (`alpha`), with the arrival estimated via
  `Geometry.travel_time_with_rotation`.
- The pickup is registered as soon as a `PICKUP` agent stands on `from_position`, also in the
  middle of a route. A* routes may pass over the goal and continue to a cell where the agent can
  rest. The agent keeps that already-reserved route, because other agents planned around it, and
  replans towards the delivery once it ends
  (`Environment.handle_agents_route_execution`). Dropping the route instead caused vertex conflicts
  when the replan failed.
- On pickup, `task.pickup_time` is set and `minimum_task_time` becomes the unobstructed A* time
  pickup→delivery (from the current orientation). For `TRIP_KARMA` the agent's karma is reset
  (`mem:simulation/negotiation`). `minimal_path_cost` (agent→pickup→delivery, unobstructed) is set on
  assignment and is used only by the `*2` cost transform.
- A task is finished when its `current_position` equals `to_position`. The agent is released
  and the task moves into `env.completed_tasks[agent_id]`.
- Randomness: always use `env.rng` (`np.random.default_rng(seed)`). Runs are deterministic per seed;
  never use the global `np.random` in simulation code.

## A* (`AStarPathPlanner.astar`)

- State (x, y, θ, t, goal_reached). The visited set includes `goal_reached`, so a state that has not
  reached the goal cannot shadow one that has. Priority = t + `heuristic`, which is the Manhattan
  distance to the goal before it is reached and 0 afterwards (the search for a free resting cell has
  no known distance). This keeps A* optimal: a brute-force check over 4500 random reservation grids
  gave 0 mismatches. Branches: wait, rotate ±1, forward.
- Reservation grid `(t, x, y)` of agent ids, **−1 = free**
  (`GridTools.create_3D_reservation_grid`). Other agents occupy their route cells and then stay on
  their final cell to the horizon end. Forward moves also reject swaps (edge conflicts).
- The goal counts only if the cell stays free until the horizon (`goal_remains_free`): "reach goal,
  then rest safely".
- Horizon = `min(params_astar.planning_horizon, reservation depth)`. Reservation depth =
  `Environment.get_sufficient_planning_horizon()` = max(longest route, planning_horizon) + buffer.
- `max_iterations` caps expansions; the result is `None` on timeout or no path.
- `ignore_counter=True` for evaluation-only shortest paths (min task time, min path cost).
- **A* call counter is thread-local** (`threading.local`) so analysis_1's `ThreadPoolExecutor` seeds
  do not mix counts. Analyses 3/4 and the sweep use process pools. Do not turn it into a plain class
  attribute.
- Path ↔ route: `convert_path_to_route` drops the start state. `convert_route_to_path(agent)` replays
  an agent's route from its current pose.

## Conflicts

- `GridTools.detect_conflicts`: vertex (same cell, same t) and edge (swap) conflicts, at most one per
  other agent (the earliest). Positions after a path ends are held at the last state.
- `visualize_simulation.check_violation` asserts no vertex or edge conflict after each step.
  It is the only runtime collision check (commented out in time_distribution).

## Centralised CBS (`CENTRALIZED`)

`Planner_CBS` replans all non-idle agents each step on an empty grid. Its conflicts are vertex plus
"just-vacated" (cell occupied at t by A and at t+1 by B), with a path end held for
`MAX_IDLE_TIME_CONSIDERED`. It raises if no solution is found within `max_iterations`. Not used in
any evaluation, and support is unverified (`mem:open_issues`).
