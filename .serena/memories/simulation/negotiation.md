# Controllers and negotiation

## Controller table (`constants.MAPF_CONTROLLER_*`, dispatched in `Environment.handle_agents`)

| constant value | paper name | rule | used in evaluations |
|---|---|---|---|
| `DECENTRALIZED_TOKEN_PASSING` | Token Passing | plan around all committed routes, no negotiation | yes |
| `DECENTRALIZED_NEGOTIATE_EGOISTIC` | Egoistic (Eq. 2) | other replans iff Δ_other ≤ 0 | yes |
| `DECENTRALIZED_NEGOTIATE_ALTRUISTIC` | Altruistic (Eq. 3) | smaller Δ replans, tie random (`env.rng`) | yes |
| `DECENTRALIZED_NEGOTIATE_TRIP_KARMA` | **Karma** (Eq. 5/6) | karma rule, balance reset on every pickup | yes |
| `DECENTRALIZED_NEGOTIATE_KARMA` | – | karma rule, balance never reset | no (only analysis_2 logs + legacy sweep) |
| `DECENTRALIZED_NEGOTIATE_EGOISTIC2` / `ALTRUISTIC2` | – | egoistic/altruistic on the relative-deviation cost transform | no (ALTRUISTIC2 only in analysis_2 logs + legacy sweep) |
| `CENTRALIZED` | CBS (§II-B only) | `Planner_CBS` (`mem:simulation/core`) | no |

The figures use a fixed label and style for each paper controller. Colours (Paul Tol muted) plus
marker / hatch live in `figures/paper_style.py`: Token Passing rose `#CC6677` `D` `xxx`, Egoistic
green `#117733` `^` `\\\`, Altruistic olive `#999933` `s` `///`, Karma indigo `#332288` `o` no
hatch (darkest). All lines stay solid (a deliberate choice: mixed dash patterns looked
inconsistent). The set is colour-blind safe (AAMAS rule), and the markers and hatches keep it
readable in greyscale. Keep them identical across `figures/`. The
old name `DECENTRALIZED_RESPECT` (still in some archived run files) is token passing.

## Negotiation protocol (`handle_agents_route_planning_decentralized_negotiate`, paper Alg. 1)

For each non-idle agent i with an empty route and a target:
1. `considered = []`. Plan shortest path π_i around `considered` agents only.
2. `detect_conflicts(π_i)` against **all** agents. If there are none, commit π_i.
3. Prioritise conflicts by i's detour cost if it had to avoid that agent (`prioritize_conflicts`,
   Eq. 1), and take the costliest.
4. Both sides compute `determine_cost_to_change`: Δ = (length of the alternative route that avoids
   the other's path, incl. resting on its end cell) − current route length. The value is **1000** if
   there is no alternative or the agent has no target (idle agents get a parking path instead).
5. `negotiation_function(cost_other, cost_mine[, agents, params_karma])` returns **True = the other
   (conflicting) agent replans**. Then the other agent adopts its alternative path immediately.
   Otherwise the other agent is added to `considered`. If the other agent has no alternative path,
   the result is always False.
6. Loop for at most `max(10, 2·n_agents)` iterations. If that fails, or A* returns None, fall back to
   `plan_route_decentralized_token_passing`.

`cost_mine` / `cost_other` in code = Δ_i / Δ_j in the paper (i = the initiating agent).

## Karma (`NegotiationStrategy.negotiate_karma`)

- Adjusted cost = Δ + τ·k, where τ = `params_karma["karma_influence"]` and k = `agent.karma_balance`
  (int, starts at `initial_karma` = 0).
- `adj_mine − adj_other > delta_threshold` → other replans; `<` → self replans; `==` → random.
  `delta_threshold` is **not in the paper**. All committed runs use 0, which is exactly Eq. 5
  (τ = 0 ≡ altruistic). A non-zero value makes the rule asymmetric.
- Payment (`_karma_payment_rule`, rule 3 = paper Eq. 6): the replanner receives its own Δ and the
  winner pays the same amount (zero-sum, pay-to-peer). A high balance therefore makes an agent less
  likely to replan next time. Rules 1/2/4 are commented-out alternatives; rule 1 needs
  `params_karma["karma_payment"]` (present only in the legacy sweep settings).
- The per-trip reset happens in `Agent.assign_task` / `Agent.update_target_position` at pickup, keyed
  on the literal string `"DECENTRALIZED_NEGOTIATE_TRIP_KARMA"` rather than the constant.
- Paper τ used for the benchmark figures: 0.5. The sweep covers τ ∈ {0.0, 0.1, …, 1.0}.

## Cost transform (`cost_transform=True`, the `*2` controllers)

Δ becomes the change in realised/minimal cost ratio: (forecast + Δ)/min − forecast/min, using
`minimal_path_cost` and `get_forecasted_path_total_cost`. It is skipped when the other agent has no
`minimal_path_cost`.

## Semantics to keep straight

- "Altruistic" means the pair minimises the joint cost: the one with the smaller detour gives way.
  It does not mean "always yield".
- Every negotiation controller adds many A* calls (conflict prioritisation plans hypothetical
  paths). Egoistic costs the most.
