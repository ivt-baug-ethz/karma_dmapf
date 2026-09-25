# Controllers and negotiation

## Controller table (`constants.MAPF_CONTROLLER_*`, dispatched in `Environment.handle_agents`)

| constant value | paper name | rule | used in evaluations |
|---|---|---|---|
| `DECENTRALIZED_TOKEN_PASSING` | Token Passing | plan around all committed routes, no negotiation | yes |
| `DECENTRALIZED_NEGOTIATE_EGOISTIC` | Egoistic (Eq. 2) | other replans iff Δ_other ≤ 0 | yes |
| `DECENTRALIZED_NEGOTIATE_UTILITARIAN` | Utilitarian (Eq. 3) | Δ_mine = `inf` → other replans (an idle one parks); else smaller Δ replans, tie random (`env.rng`) | yes |
| `DECENTRALIZED_NEGOTIATE_KARMA` | **Karma** (Eq. 5/6) | karma rule, balance never reset | yes |
| `DECENTRALIZED_NEGOTIATE_TRIP_KARMA` | – (the paper's original Karma) | karma rule, balance reset on every pickup | no (legacy sweep + commented toggles only) |
| `CENTRALIZED` | CBS (§II-B only) | `Planner_CBS` (`mem:simulation/core`) | no |

The figures use a fixed label and style for each paper controller. Colours (Okabe-Ito) plus
marker / hatch live in `figures/paper_style.py`: Token Passing black `#000000` `D` `xxx`, Egoistic
blue `#0072B2` `^` `\\\`, Utilitarian green `#009E73` `s` `///`, Karma orange `#D55E00` `o` no
hatch (`paper_style.py` keys both Karma constants to the same style). Karma is orange on purpose, so it is the most visible series; the authors chose this over
alternatives (Tol muted, Tol high-contrast) compared side by side. Trade-off they accepted: in
greyscale, Token Passing (black) is the darkest series, and Karma and Utilitarian are similar
mid-greys that only their markers (circle vs square) separate. All lines stay solid (a deliberate choice: mixed dash patterns looked
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
   the other's path, incl. resting on its end cell) − current route length. The avoided path is
   written into the reservation grid **only in free cells**. Overwriting the ids of other agents would
   break A*'s swap check, which needs the same id on both cells, and would let edge conflicts through. 
   - No alternative: `COST_TO_CHANGE_INFEASIBLE` (`constants.py`), written `inf` below. It is
     `sys.maxsize`, not `float("inf")`, so Δ, payments and balances stay `int`. It is only ever compared
     (forced branches first, never paid), so it behaves exactly like `inf` (verified bit-identical).
   - Idle agent: Δ is its **real parking detour**, or `inf` without a parking path.
   - `Environment.make_decision` passes `inf` for an idle other agent to the rules without agent
     parameters. Egoistic and utilitarian therefore behave exactly as with the former `1000`
     (verified task-by-task identical).
5. `negotiation_function(cost_other, cost_mine[, agents, params_karma])` returns **True = the other
   (conflicting) agent replans**. Then the other agent adopts its alternative path immediately.
   Otherwise the other agent is added to `considered`. If the other agent has no alternative path,
   the result is always False.
   The result is named `other_resolves_conflict` in every rule and in the loop. Ties are broken with
   the seeded `env.rng` only: `negotiate_utilitarian` takes it as a required `rng` argument (no global
   `np.random` fallback), Karma uses `agent_self.environment.rng`.
6. Loop for at most `max(10, 2·n_agents)` iterations. If that fails, or A* returns None, fall back to
   `plan_route_decentralized_token_passing`.

`cost_mine` / `cost_other` in code = Δ_i / Δ_j in the paper (i = the initiating agent).

## Karma (`NegotiationStrategy.negotiate_karma`)

- Adjusted cost = Δ + τ·k, where τ = `params_karma["karma_influence"]` and k = `agent.karma_balance`
  (`int`, like every Δ it is paid in; starts at `initial_karma` = **20** in every script; trip Karma resets to it).
- Forced decisions come first and skip the karma comparison:
  - Δ_mine = `inf` (i cannot avoid j) → j gives way. An idle j steps aside to its parking cell.
  - j idle and Δ_mine finite → i gives way. An idle agent has no task to delay and does not give way.
  - **No karma changes hands in a negotiation with an idle j** (`negotiate_karma` returns before
    the payment): neither when the idle blocker wins nor when it is forced aside by an infeasible
    i. Its detour is not counted as delay either. Both are placeholders, to be revisited under
    `TO_EXPLORE.md` item 6. i is never idle (`planning_relevant_agents` skips idle agents).
- Otherwise: `adj_mine − adj_other > delta_threshold` → other replans; `<` → self replans; `==` → random.
  `delta_threshold` is **not in the paper**. All committed runs use 0, which is exactly Eq. 5
  (τ = 0 ≡ utilitarian, bit-identical with and without the reset: utilitarian uses the same
  `inf`-first rule). A non-zero value makes the rule asymmetric.
- Payment (`_karma_payment_rule`, rule 3 = paper Eq. 6), between two busy agents only: the
  replanner receives its own Δ and the winner pays the same amount (zero-sum, pay-to-peer).
  - The payment is `max(0, Δ_yielder)`, so it is never negative.
  - It is also limited to the payer's balance, so **balances never become negative**.
  - The yielder's Δ is always finite: forced yielders reached the decision with an alternative. So an
    `inf` bid can never be lost or paid.
  - When the initiating agent i gives way, it does not adopt the alternative whose length it bid. It
    adds j to `considered` and replans its shortest path around j, so the payment is the *estimated*
    detour. When j gives way, it adopts exactly the alternative it bid (`change_path_to_satisfy`).
  - Without a reset, balances stay bounded (10×10/30, T = 200: 0..55 instead of ±990) and their sum
    stays exactly 20·n (verified with the idle no-payment rule). With the trip reset the sum is not conserved. A high balance therefore makes an agent less
  likely to replan next time. Rules 1/2/4 are commented-out alternatives; rule 1 needs
  `params_karma["karma_payment"]` (present only in the legacy sweep settings).
- The per-trip reset (`TRIP_KARMA` only) happens in `Agent.assign_task` / `Agent.update_target_position`
  at pickup, keyed on the literal string `"DECENTRALIZED_NEGOTIATE_TRIP_KARMA"` rather than the constant.
- Paper τ used for the benchmark figures: 0.5. The sweep covers τ ∈ {0.0, 0.1, …, 1.0};
  `delay_evaluation` runs τ ∈ {0.1, 0.25, 0.5, 0.75, 0.9}. Explorations put the no-reset optimum at τ ≈ 0.1–0.25.

## Negotiation case counters

`Environment.negotiation_cases` (a `Counter`) counts every negotiation of every negotiation
controller by a key `"<busy|idle> other, self <feasible|infeasible>, other <feasible|infeasible>,
<self|other> yields"` (self = the planning agent, infeasible = no alternative path). `delay_evaluation`
prints the totals per series. Behaviour-neutral.

## Why Δ stays in raw time steps (removed `*2` controllers)

`EGOISTIC2` / `UTILITARIAN2` (and `minimal_path_cost`, `get_forecasted_path_total_cost`) were removed
on 2026-09-25. Their cost transform (forecast + Δ)/min − forecast/min reduces to Δ / min_task_length:
- EGOISTIC2 was bit-identical to EGOISTIC (the sign of Δ is unchanged).
- UTILITARIAN2 protected short tasks: slightly lower mean %-increase, but higher service-time std,
  higher per-agent cumulative-delay Gini and +13 % A* calls on 10×10/30.

Raw Δ is the Karma currency: balances carry across tasks without a reset, and one unit must mean the
same time on every task. It also keeps utilitarian ≡ Karma at τ = 0. Do not reintroduce a per-task
normalisation of Δ.

## Semantics to keep straight

- "Utilitarian" means the pair minimises the joint cost: the one with the smaller detour gives way.
  It favours neither agent, only the better outcome for the system, and does not mean "always yield".
- Every negotiation controller adds many A* calls (conflict prioritisation plans hypothetical
  paths). Egoistic costs the most.
