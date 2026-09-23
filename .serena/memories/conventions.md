# Conventions

## Write like the code that is already there (overrides every default)

New code is indistinguishable from its neighbours or it is wrong. Before writing anything, read the
nearest existing counterpart (the sibling negotiation rule, the sibling analysis script, the sibling
figure script) and copy its shape: same argument order, same naming, same comment density, same
error messages, same import order. Deviating "because it is cleaner" is a defect, not an improvement.

- **No new duplication.** Metric and summary logic belongs in `src/simulation/metrics.py`; reuse it.
  The existing copy-pasted step loops and settings dicts are known debt (`mem:open_issues`). Match
  them when editing a script, but do not add another copy of helper logic.
- **No speculative abstraction.** No base class for one implementation, no config knob nobody asked
  for. The negotiation rules are plain `@staticmethod`s on `NegotiationStrategy` and the dispatch is
  an `if/elif` chain in `Environment.handle_agents`; extend both in place.
- **Simplest thing that works.** Prefer a pinned dependency (`tqdm`, `numpy`, `scipy`, `pandas`)
  over a hand-rolled equivalent.
- **Human style.** Plain lower-case `#` comments explaining the *why*. Leave no scaffolding "for
  later" and no dead or commented-out code in code you write. Existing commented-out alternatives
  (payment rules, debug prints) stay unless the user asks.

## Imports and typing

- Imports are absolute from the repo root (`from src.simulation.geometry import Grid`,
  `from src.planners.astar import AStarPathPlanner`), never relative. Imports needed only for annotations
  go under `if TYPE_CHECKING:` with `from __future__ import annotations` to avoid cycles
  (agent ↔ environment ↔ task ↔ geometry).
- Type-annotate signatures and attributes (`self.id: int = ...`) with `typing` generics
  (`List`, `Optional`, `Dict`, `Tuple`) and `NDArray[np.int_]`.
- Docstrings are sparse and informal (triple-quoted prose or a short `"""..."""`), not Google
  style. Match the file.

## Script layout

- Entry points live in `src/scripts/`, named after what they do (no numbers, no leading
  underscore). They rely on `PYTHONPATH=.` (`mem:core`); never touch `sys.path`.
- Simulation/analysis scripts keep their configuration at module level. Older scripts use
  a lower-case `simulation_settings` dict inside `###`-banner sections (`###### IMPORTS ######`,
  `###### PARAMETERS ######`, `###### MAIN ######`). Newer ones (karma_influence, tradeoffs, sweep) use upper-case
  constants, a frozen `ExperimentConfig` dataclass, `main()`, `logging` with `%s` placeholders and
  `tqdm`.
- Outputs are root-anchored, never cwd-relative (`mem:core`): figure inputs to `results/<script name>/`,
  everything else to `results/runs/`.
- Controller strings are always referenced through `src.simulation.constants.MAPF_CONTROLLER_*`.
- Randomness always goes through `environment.rng`.

## Figure scripts (`figures/`)

- A module docstring names the figure, the `results/<analysis>/` files it reads, the
  `src/scripts/` command that produces them and the constants to set per run.
- Module-level data folder and style constants, `main(output_dir, show)`, and argparse
  `--output-dir/-o` plus `--no-show`. They switch to Agg when headless.
- The label and colour for each controller are fixed (`mem:simulation/negotiation`). Reuse them
  verbatim.
- A new figure script must also be added to `.github/workflows/figure-plots.yml`.

## Comments

Describe present behaviour only. No changelog or history comments ("was X", "now folded into",
dates, before/after states); git records that.

## Lint and format

- `black` (CI: `psf/black@stable`) on `src` and `figures`.
- `PYTHONPATH=. pylint src --errors-only` must be clean (without it the `src.` imports do not resolve), and it is clean today. There is no `.pylintrc` and the
  full-score run is not a gate. Scope disables to one line with a specific code, never file-wide.
- `pyrightconfig.json` points Pyright/Pylance at `./venv`; the workspace root resolves the `src.` imports. Type checking
  is not a CI gate, but Pylance (standard mode) is clean on `src/` and `figures/`; keep it so.
  Pylance uses its bundled pandas stubs (pandas has no `py.typed`). A bare `npx pyright` run uses
  pandas' inline types instead and additionally flags the tuple unpack of `groupby` keys in
  `karma_influence_sweep.py` ("Hashable is not iterable"); that one is accepted, not cast away.
  Prefer `df.loc[mask]` over `df[mask]` for boolean row filters: it types as a DataFrame under both.

## Commits

Conventional style with an optional scope and PR number: `feat: …`, `fix: …`, `refactor: … (#6)`,
`chore: …`, `ci: …`, `evaluation: …`.
