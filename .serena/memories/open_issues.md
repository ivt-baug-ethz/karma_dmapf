# Open issues and planned work

Remove an entry once it is resolved. Add new ones only when they are real and non-obvious.

## Planned: restructure into a standard repository layout

The current layout is a research dump:
- flat imports that force cwd `src/`
- the step loop copy-pasted into every script
- three copies of the settings dict
- per-script `gini/summarize` duplicates (analysis 3)
- analysis configuration by editing constants
- stray tracked files (`Figure_3.png` at root)

Target:
- a proper package (`python -m ...`, no flat imports)
- one shared simulation runner and settings source
- one output convention: figure inputs in `log_files/`, scratch in `results/`

The root-anchored output paths are the interim fix. Do not start this refactor unasked.

## Controller support to restore/verify

All eight controllers must keep working, but only the four paper controllers are used in
evaluations (`mem:simulation/negotiation`). These are unverified against the current code and may
need updating:
- `CENTRALIZED` (CBS), which raises if no solution is found
- `DECENTRALIZED_NEGOTIATE_KARMA`
- `DECENTRALIZED_NEGOTIATE_EGOISTIC2` / `ALTRUISTIC2` (cost transform)

This is planned as an early task: a short smoke run per controller with `check_violation`. Fixing
them must not add them to any analysis or figure.

## Known quirks

- `_analysis_1` names its output JSON after the last controller of its loop, so run one controller per
  invocation (`mem:analysis_and_figures`).
- The TRIP_KARMA reset compares `settings["mapf_control"]` with a string literal instead of
  `MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA`.
- `README.md` run instructions omit the `cd src` requirement and name `Figure_3_v2.py`, which does not exist.
