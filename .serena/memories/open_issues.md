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
- `Figure_4` (supplementary): the long metric names used as y-labels overlap between its stacked
  subplots. This is a layout issue, not a styling one.

## Paper text vs figure style (outside this repo)

The figures use a colour-blind and greyscale safe style (`figures/paper_style.py`,
`mem:simulation/negotiation`). The LaTeX sources are not in this repo, so their captions and body
text have not been checked for references to colour names from an earlier palette ("red",
"green", "blue", "olive"). The authors must check the `.tex` by hand and make one real
black-and-white print of the compiled PDF.
