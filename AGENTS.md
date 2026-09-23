# AGENTS.md

Instructions for every coding agent working in this repository. This file is the single rulebook:
`CLAUDE.md` imports it and adds only Claude Code specifics, and `.github/copilot-instructions.md`
points here.

## Project

**karma_dmapf** is the Python 3.13 research code behind the paper *"Karma Mechanisms for Decentralised, Cooperative Multi Agent Path Finding"*. It simulates a lifelong, orientation-aware warehouse pickup-and-delivery (MAPD) scenario on a grid. Conflicts are resolved by token passing, by pairwise negotiation (egoistic, altruistic, Karma) or by centralised CBS. Key dependencies (pinned in `requirements.txt`): `numpy`, `scipy`, `matplotlib`, `pandas`, `seaborn`, `imageio`, `tqdm`. Everything runs locally as scripts: simulation and analyses in `src/`, paper figures in `figures/`. There is no server, deployment target or test suite.

`src/` holds two packages, `simulation/` and `planners/`, plus the entry points in `src/scripts/`. Imports are absolute from the repository root (`from src.simulation.environment import Environment`), so every script runs from the repo root with the venv active and `export PYTHONPATH=.`: `python src/scripts/<script>.py`. Nothing is installed and `sys.path` is never manipulated. All outputs are anchored at the repository root. Figure inputs go to `results/<analysis>/`, which is committed. Run output goes to `results/runs/` and manual copies of old runs go to `results/archive/`; both are git-ignored. Do not add top-level directories without being asked.

Status: **active development**. Consult the project memories for the up-to-date picture before assuming any structure.

## Project knowledge lives in the memories (read first, every session)

Project knowledge is maintained as markdown **memories** in `.serena/memories/`. They are the single source of truth, and the *only* one. Do not create parallel tracking stores (no `.ai/` directory, no scratch notes, no second rules file), and do not copy memory content into this file. Agents with serena tools use `list_memories` / `read_memory` / `write_memory`. Any other agent reads and edits the files directly, e.g. `mem:simulation/core` is `.serena/memories/simulation/core.md`.

The memories are **committed** (`.serena/.gitignore` excludes only `cache/` and `project.local.yml`), so memory updates show up in `git status` alongside the code they describe.

**Before starting a task**: read `core`. It is the graph root: it maps the repository and links to `tech_stack`, `conventions`, `suggested_commands`, `task_completion`, `simulation/core`, `simulation/negotiation`, `analysis_and_figures`, `open_issues`. Follow only the links your task needs; do not read them all.

**While working**: follow the `conventions` memory. Look up library APIs (`numpy`, `scipy`, `matplotlib`, `pandas`, `seaborn`, `imageio`) in their documentation (e.g. via context7) instead of guessing signatures.

**Before finishing a task (definition of done)**: work through the `task_completion` memory, and update whichever memories the change affects: structure → `core`, style → `conventions`, commands → `suggested_commands`, domain behaviour → the topic memory, resolved or new known problems → `open_issues`.

**A stale memory is a bug**: fix it in the same task. Memory upkeep is an edit to an existing memory far more often than a new one; `serena memories check` reports dangling `mem:` references.

## Keep the code simple and human-like (guiding principle)

**Prefer the simplest solution that works; do not over-engineer.** Reach for a
well-established library instead of hand-rolling equivalent functionality (e.g. use
`tqdm` for a progress bar rather than writing a custom one). Write code the way a
human maintainer would: plain, readable, no speculative abstraction, no options or
configuration nobody asked for. When a one-liner does the job, use the one-liner.

**New code must be indistinguishable from the code already in the file.** Before writing anything,
read the nearest existing counterpart (the sibling negotiation rule, the sibling analysis script,
the sibling figure script) and match it exactly: argument order, naming, docstring layout, comment
density, error-message wording, import order. "Cleaner than the neighbours" is a defect here, not an
improvement. Leave no dead or commented-out code behind in code you write.
The full rules live in the `conventions` memory; read it before writing code.

## Code comments describe CURRENT functionality only (hard rule)

**Never write changelog / "what I did" / "how it was" comments in the code files.** A comment must
describe what the code does *now*, not its history. Do **not** write things like "was 1.8", "now
folded into X", "previously duplicated", "reverted to", "tuned 2026-07-…", "no longer uses", "this
flipped the metric", or dates and before/after states. If you changed something, the diff and the
git history record that. The source comments must read as if the current state was always
the design. Prefer no comment over a historical one; keep comments plain and about the present
behaviour.

## Paper data and controllers (hard rules)

- **The tracked `results/` must always match the current code, but never re-run an analysis without asking.**
  The analyses take minutes to hours. Whenever a change touches simulation code or an analysis
  script, end your final summary with a reminder naming the analyses whose `results/<analysis>/` are now
  stale, and offer to regenerate them. The `analysis_and_figures` memory maps code → analysis → figure.
- **All eight controllers keep code support**, but the evaluations and figures use only the four
  paper controllers: token passing, egoistic, altruistic, and Karma (`TRIP_KARMA`). Never add
  `CENTRALIZED`, `NEGOTIATE_KARMA` or `*2` to a script or scenario that does not use them already
  (`simulation/negotiation` memory).

## Git (hard rules)

- **Never create a git worktree** or otherwise isolate work into a separate working copy, not even
  for background jobs. Apply all changes directly to the branch the user currently has checked out.
- **Never commit or stash.** The user owns both. Leave finished work uncommitted in the tree.

## Environment (quick reference; full commands in the `suggested_commands` memory)

- Local dev uses a Python 3.13 virtual environment. `venv/` is git-ignored; do not commit it. Never install packages globally, and pin any new dependency in `requirements.txt`.

```bash
python3.13 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.   # from the repo root, before running any script
```

- No test suite. Formatting: `black src figures` (CI checks it). Linting: `PYTHONPATH=. ./venv/bin/pylint src --errors-only` must be clean. That is the CI gate.
- Figures: `python figures/Figure_N.py --no-show --output-dir <dir>` must keep rendering (CI workflow `figure-plots.yml`).
- Scratch outputs go to `results/runs/` (automatic) or `results/archive/` (manual copies), which are git-ignored; do not commit them.
