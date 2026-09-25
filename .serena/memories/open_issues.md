# Open issues and planned work

Remove an entry once it is resolved. Add new ones only when they are real and non-obvious.

## Planned: deduplicate the scripts

The directory layout is settled (`mem:core`), and the step itself is shared (`Environment.step`),
but the scripts still carry research debt:
- the setup + loop + A* counter boilerplate around `step()` in every script
- three copies of the settings dict
- per-script `gini/summarize` duplicates (karma_influence)
- analysis configuration by editing constants

Target: one shared simulation runner and settings source. Do not start this refactor unasked.

## Controller support to restore/verify

All six controllers must keep working, but only the four paper controllers are used in
evaluations (`mem:simulation/negotiation`). These are unverified against the current code and may
need updating:
- `CENTRALIZED` (CBS), which raises if no solution is found. Confirmed broken on 2026-09-25: with the
  default `params_cbs` it raises a CBS timeout within the first 2–28 steps on 5×5/10 and 10×10/30
  (seeds 41–43), on the committed code (old step loop) as well as with `Environment.step`.

`NEGOTIATE_KARMA` and `TRIP_KARMA` pass a 100-step `check_violation` smoke run on 5×5/10 (2026-09-25).
This is planned as an early task: a short smoke run per controller with `check_violation`. Fixing
them must not add them to any analysis or figure.

## Known quirks

- `efficiency_benchmark` names its output JSON after the last controller of its loop, so run one controller per
  invocation (`mem:analysis_and_figures`).
- The TRIP_KARMA reset compares `settings["mapf_control"]` with a string literal instead of
  `MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA`.
- **Cleanup when asked**: `NEGOTIATE_KARMA` (no reset) is now the paper's Karma and `TRIP_KARMA` is
  unused by every analysis and figure. Rename/remove it (constant, dispatch branch, the two reset
  blocks in `agent.py`, the `paper_style.py` entries, commented toggles, the legacy sweep) only
  when the user asks for the cleanup.
- **Tracked `results/` are stale** (efficiency_benchmark, time_distribution, karma_influence,
  karma_influence_tradeoffs): step order, spare-task pool, idle no-payment rule, task time from
  assignment and the Karma controller changed. Figures 1–4 look up `NEGOTIATE_KARMA` data that the
  committed files do not contain: Figures 1 and 2 raise `FileNotFoundError` (the CI figure job is
  red), Figures 3 and 4 render without a Karma series, until the analyses are regenerated.
- `Figure_4` (supplementary): the long metric names used as y-labels overlap between its stacked
  subplots. This is a layout issue, not a styling one.

## Paper text vs figure style (outside this repo)

The figures use a colour-blind and greyscale safe style (`figures/paper_style.py`,
`mem:simulation/negotiation`). The LaTeX sources are not in this repo, so their captions and body
text have not been checked for references to colour names from an earlier palette ("red",
"green", "blue", "olive"). The authors must check the `.tex` by hand and make one real
black-and-white print of the compiled PDF.
