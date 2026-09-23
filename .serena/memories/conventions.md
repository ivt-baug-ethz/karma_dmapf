# Conventions

## Write like the code that is already there (overrides every default)

New code is indistinguishable from its neighbours or it is wrong. Before writing anything, read the
nearest existing counterpart (the sibling negotiation rule, the sibling analysis script, the sibling
figure script) and copy its shape: same argument order, same naming, same comment density, same
error messages, same import order. Deviating "because it is cleaner" is a defect, not an improvement.

- **No new duplication.** Metric and summary logic belongs in `src/analysis_helpers.py`; reuse it.
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

- `src/` uses flat module imports (`from geometry import Grid`). Imports needed only for annotations
  go under `if TYPE_CHECKING:` with `from __future__ import annotations` to avoid cycles
  (agent ↔ environment ↔ task ↔ geometry).
- Type-annotate signatures and attributes (`self.id: int = ...`) with `typing` generics
  (`List`, `Optional`, `Dict`, `Tuple`) and `NDArray[np.int_]`.
- Docstrings are sparse and informal (triple-quoted prose or a short `"""..."""`), not Google
  style. Match the file.

## Script layout

- Simulation/analysis scripts in `src/` keep their configuration at module level. Older scripts use
  a lower-case `simulation_settings` dict inside `###`-banner sections (`###### IMPORTS ######`,
  `###### PARAMETERS ######`, `###### MAIN ######`). Newer ones (analysis 3/4) use upper-case
  constants, a frozen `ExperimentConfig` dataclass, `main()`, `logging` with `%s` placeholders and
  `tqdm`.
- Outputs are root-anchored, never cwd-relative (`mem:core`).
- Controller strings are always referenced through `constants.MAPF_CONTROLLER_*`.
- Randomness always goes through `environment.rng`.

## Figure scripts (`src_figures/`)

- Module-level data folder and style constants, `main(output_dir, show)`, and argparse
  `--output-dir/-o` plus `--no-show`. They switch to Agg when headless.
- The label and colour for each controller are fixed (`mem:simulation/negotiation`). Reuse them
  verbatim.
- A new figure script must also be added to `.github/workflows/figure-plots.yml`.

## Comments

Describe present behaviour only. No changelog or history comments ("was X", "now folded into",
dates, before/after states); git records that.

## Lint and format

- `black` (CI: `psf/black@stable`) on `src` and `src_figures`.
- `pylint src --errors-only` must be clean, and it is clean today. There is no `.pylintrc` and the
  full-score run is not a gate. Scope disables to one line with a specific code, never file-wide.
- `pyrightconfig.json` points Pyright/Pylance at `./venv` with `extraPaths: ["src"]`. Type checking
  is not a CI gate.

## Commits

Conventional style with an optional scope and PR number: `feat: …`, `fix: …`, `refactor: … (#6)`,
`chore: …`, `ci: …`, `evaluation: …`.
