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

## Known bugs and data problems (`TO_FIX.md`, open questions in `TO_EXPLORE.md`)

The confirmed list lives in `TO_FIX.md`, ordered by priority; its item numbers are stable (item 2
was resolved and removed). Do not fix anything from it unasked. Headlines:
- item 1: the stale `TRIP_KARMA` result files (Karma times an exact affine shrink towards the mean,
  non-integer counts) are still in `results/`. The four paper controllers' files were regenerated
  from the code on 2026-09-27; the provenance of the old files is still to be clarified.
- item 3: the Figure_1 scale factors

Open simulation bugs with replayable examples are in `BUG_REPORTS.md` (#7–#9; fixed bugs keep their
numbers in `mem:paper_changes`).

Any code fix makes all of `results/` stale.

`TO_EXPLORE.md` is the idea backlog (extended on request only). Its exploration (plans, code, findings, per-item verdicts, open questions, the 2026-09-25 results regeneration) is documented in `mem:explorations`; read that memory before touching any of it. Item 21 of the list is `[ESSENTIAL, final]`: drop the Figure 1 `scale_factors` and rolling median and run every paper scenario at one common T before the code is finalised.

## Remaining deadlocks and candidates from the 2026-09-26 tuning

- **Stuck agents at extreme density** (5×5 with ≥ 15 agents, 10×10/60) are two different effects
  (`BUG_REPORTS.md` #9):
  - Task starvation (all controllers). Tasks spawn only on free interior cells, and parked idle
    agents fill them, so few tasks exist. A far-away parked agent can stay idle for more than
    100 steps. Idea: park idle agents on the border.
  - Idle-blocker gridlock (egoistic only). An idle other agent gets Δ = `inf` and egoistic never
    forces it aside, even when the busy agent has no alternative. A harness test of the forced
    branch on v6 (E43, harness switch `egofix`) removes the gridlock (5×5/20: 113 → 214 trips) and
    makes egoistic 0.83× utilitarian's spread at −3.5 % delay on 10×10/30. It changes a paper
    baseline, so it is the authors' call.
- On the final code v6, in 1039 checked runs (T = 300 and 1000, 5×5 to 15×15/80), the only busy
  stuck agents are in plain egoistic on 5×5/20 (the idle-blocker gridlock above). All other
  stuck agents (38) are idle agents waiting for a task (task starvation).
- **Untracked payment-rule result:** a harness-only rule beats the paper's Eq. 6 on every
  scenario (`KARMA_TUNING.md`, E18/E38–E42). Adopting it is the authors' decision.
- **Metric:** a trip still open at T is not counted, so a starving agent shows a *low*
  cumulative delay. Keep the stuck-run check (an agent with no completion in the last 100
  steps) next to any spread metric.
- **Candidate, not adopted:** adding an agent that gave way to the planning agent's considered
  set. On the final code v6 (E40, 20 seeds) it cuts A* calls by 16 % (10×10/30) and 9 % (5×5/10).
  It also makes utilitarian less fair (spread 1.04× and 1.23×, +4 % delay on 5×5). It is a pure
  compute saving with a fairness cost.

## Known quirks

- `efficiency_benchmark` names its output JSON after the last controller of its loop, so run one controller per
  invocation (`mem:analysis_and_figures`).
- The TRIP_KARMA reset compares `settings["mapf_control"]` with a string literal instead of
  `MAPF_CONTROLLER_DECENTRALIZED_NEGOTIATE_TRIP_KARMA`.
- **Cleanup when asked**: `NEGOTIATE_KARMA` (no reset) is now the paper's Karma and `TRIP_KARMA` is
  unused by every analysis and figure. Rename/remove it (constant, dispatch branch, the two reset
  blocks in `agent.py`, the `paper_style.py` entries, commented toggles, the legacy sweep) only
  when the user asks for the cleanup.
- **Tracked `results/` regenerated on 2026-09-27** (02:41–05:19, 2 h 38 min at ≤ 11 cores): all five
  analyses with the code at 2437770 **without** 512bf8c (parking ranking), τ = 0.15 and seeds 41–45.
  This is not yet the final 10-seed run, and the data differ slightly from the current code
  (`mem:paper_changes`). The driver is the git-ignored `results/archive/karma_tuning/regen5.sh`, at most
  11 busy cores. Wall times are in `logs/regen/walltimes.txt`. Earlier regenerations on the
  intermediate versions v2b–v5 were superseded (`logs/regen_*_superseded`, `regen_v2b_invalid`).
  The old `TRIP_KARMA` files in `efficiency_benchmark/` and `time_distribution/` were left in
  place. They are stale and no figure reads them. All five figures now find their `NEGOTIATE_KARMA` data.
- `Figure_4` (supplementary): the long metric names used as y-labels overlap between its stacked
  subplots. This is a layout issue, not a styling one.

## Paper text vs figure style (outside this repo)

The figures use a colour-blind and greyscale safe style (`figures/paper_style.py`,
`mem:simulation/negotiation`). The LaTeX sources are not in this repo, so their captions and body
text have not been checked for references to colour names from an earlier palette ("red",
"green", "blue", "olive"). The authors must check the `.tex` by hand and make one real
black-and-white print of the compiled PDF.
