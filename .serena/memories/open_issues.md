# Open issues and planned work

Remove an entry once it is resolved. Add new ones only when they are real and non-obvious.

## Planned: deduplicate the scripts

The directory layout is settled (`mem:core`), but the scripts still carry research debt:
- the step loop copy-pasted into every script
- three copies of the settings dict
- per-script `gini/summarize` duplicates (karma_influence)
- analysis configuration by editing constants

Target: one shared simulation runner and settings source. Do not start this refactor unasked.

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

- `efficiency_benchmark` names its output JSON after the last controller of its loop, so run one controller per
  invocation (`mem:analysis_and_figures`).
- The TRIP_KARMA reset compares `settings["mapf_control"]` with a string literal instead of
  `MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA`.
