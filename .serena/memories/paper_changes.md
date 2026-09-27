# Changes to carry into the updated paper

The paper's figures and numbers were produced before every change below. Keep this list current:
add one entry per change that affects simulation behaviour, metrics, parameters, data or figures,
and remove nothing until the paper text reflects it. Bug numbers (#n) are those of
`BUG_REPORTS.md` at the repo root (uncommitted). That file now keeps only the open bugs (#7–#9);
the fixed ones are documented here under the same numbers.

## Simulation fixes before the Karma tuning (2026-09-24/25)

| commit | change | paper impact |
|---|---|---|
| fca0c81 | swap (edge) conflicts detected in `determine_cost_to_change`: the avoided path is written only into free cells | Δ and alternatives were wrong in some swaps |
| 5a1c486 | a pickup is registered when an agent passes over the pickup cell | throughput |
| 48ef676 | A* heuristic admissible with parking/resting goals (A* optimal) | path lengths, Δ |
| 5f6c043 | Karma: infeasible bids as `inf`, payments clipped at 0 and to the payer's balance, initial karma 20, balances persist (no reset = paper Karma, `NEGOTIATE_KARMA`) | Karma definition (Eq. 5/6 context) |
| 6cd339a | "altruistic" renamed "utilitarian" | naming in the text |
| 03f25ba | `*2` controllers and cost normalisation removed; Δ stays in raw time steps | methods text |
| c8b4b1a | step order (release before assign), spare-task pool, task time from the assignment, task delay, per-agent cumulative delay, `delay_evaluation` + Figure 5 | new metrics and Figure 5 |

## Simulation fixes from the Karma tuning (2026-09-27)

All of them change trajectories. Evidence and replays: `KARMA_TUNING.md`,
`results/archive/bug_reports/` (git-ignored).

| # | commit | fix | why (evidence) |
|---|---|---|---|
| 2 | 219dc58 | planning agents of a step are visited in random order (`env.rng`) | ascending-id order made low ids give way most (ρ(id, cumulative delay) −0.27…−0.40) |
| 1 | a146a27 | `Environment.determine_other_cost` leaves the planning agent out of the other agent's reservation grid; safety net `yielded_routes` restores the routes of agents that gave way if the planner ends without a route | permanent deadlock of two agents on each other's targets (5–10 % of T = 300 and 20–50 % of T = 1000 runs had a starving agent) |
| 3 | e201748 | equal-priority conflicts shuffled before the stable sort in `prioritize_conflicts` | ties went to the lowest id (ρ −0.21 → −0.03; A* calls −25 %) |
| 4 | c540e92 | an agent that has not planned yet measures Δ against its unobstructed shortest route, not 0 | it bid its whole route (9.3 instead of 3.4 steps) and won |
| 10 | 211262b | in the token-passing fallback a busy agent without any path steps aside to a free nearby cell | cyclic deadlocks of ≥ 3 agents (2 of 160 runs); token passing also affected |
| – | 512bf8c | parking cells ranked by estimated time incl. turns; the step-aside adds the distance to the goal | enhancement, affects every idle parking move |
| 11 | 2437770 | assignment candidates shuffled before the Hungarian assignment | ties gave low ids more trips (5×5/10: ρ(id, trips) −0.16) |

Not in the code: #6 (two unsafe intermediate versions of #1, never committed).
All randomness goes through `env.rng`; runs are bit-reproducible per seed within and across
processes (verified 2026-09-27: 20 configurations twice in one process and under two hash seeds).

## Scripts, parameters and data (regeneration, 2026-09-27)

- #5: `delay_evaluation.py` spawned `2 * n_agents` agents; it spawns `n_agents` like every script.
  The previously committed Figure 5 data had 10/30 agents and did not come from that code.
- Karma parameters in all scripts: τ = 0.15 (was 0.5), initial karma 20, winner pays the loser's Δ
  (Eq. 6 unchanged). `delay_evaluation` runs τ ∈ {0.1, 0.15, 0.25, 0.5, 0.75}.
- Seeds temporarily 41–45 in the five analyses. For the paper restore 41–50 (41–60 for the τ
  sweeps) and regenerate.
- Tracked `results/` and `figures/Figure_{1,2,3,5}.png` were regenerated with the code at 2437770
  **without** 512bf8c (parking ranking). They therefore differ slightly from the current code.
  Regenerate everything once more, at 10 seeds, before the paper (≈ 5–6 h on 11 cores, driver
  pattern in `mem:analysis_and_figures`). `results/animations/*.gif` were not regenerated.
- The stale `TRIP_KARMA` result files of unclear origin are still in `results/` (`TO_FIX.md` item 1).

## Findings to report (details and tables in `KARMA_TUNING.md`, 20 seeds, T = 300)

- Paper Karma on the fixed simulator: across-agent std of cumulative delay 0.89× utilitarian's on
  10×10/30 (+4.4 % mean task delay) and 0.97× on 5×5/10 (+7.5 %). The larger gains measured before
  the fixes were mostly Karma compensating the id biases (#2, #3, #11) and deadlocks (#1, #10).
- τ 0.1–0.15 is best; larger τ, first price and karma-game bid policies are worse. Initial karma only matters through the zero floor.
- A harness-only rule (the yielder is paid its Δ by all agents in equal shares, the winner pays
  nothing) reaches 0.80×/0.83× at +3–4 %, also on held-out seeds and at T = 1000. It changes Eq. 6,
  so adopting it is the authors' decision.
- No Karma variant lowers the per-trip delay spread (trip-reset Karma included).
- Egoistic is first-come-first-served (the planner gives way in 71–84 % of negotiations). It is
  the fairest and fastest controller on 15×15/80 (0.81×, −10.5 % delay) but the least fair on
  5×5/10 (1.20×, +23 %). A forced-yield branch for idle blockers (harness only) removes its
  gridlock at extreme density (`BUG_REPORTS.md` #9).

## Open items

- `BUG_REPORTS.md`:
  - #7: open trips are not counted in the delay metric;
  - #8: parallel τ sweeps can share a run folder;
  - #9: task starvation and the egoistic idle-blocker gridlock at extreme density.
- `TO_FIX.md`:
  - item 1: provenance and removal of the stale `TRIP_KARMA` files;
  - item 3: Figure 1 scale factors.
- `TO_EXPLORE.md` item 21 (final): one common T and no scale factors or rolling median in
  Figure 1.
