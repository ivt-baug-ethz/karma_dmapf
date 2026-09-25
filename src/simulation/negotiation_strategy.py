from __future__ import annotations
from typing import TYPE_CHECKING, Any
from src.simulation.constants import COST_TO_CHANGE_INFEASIBLE

if TYPE_CHECKING:
    from src.simulation.agent import Agent


class NegotiationStrategy:
    """
    Decide which agent resolves the conflict. cost_mine is the detour of the initiating agent,
    cost_other the one of the conflicting agent. other_resolves_conflict = True means the
    conflicting agent replans, False means the initiating agent replans
    """

    @staticmethod
    def negotiate_egoistic(cost_other: int, cost_mine: int) -> bool:
        other_resolves_conflict: bool
        if cost_other <= 0:
            other_resolves_conflict = True
        else:
            other_resolves_conflict = False
        return other_resolves_conflict

    @staticmethod
    def negotiate_utilitarian(cost_other: int, cost_mine: int, rng: Any) -> bool:
        # who is worse off?
        other_resolves_conflict: bool
        if cost_mine == COST_TO_CHANGE_INFEASIBLE:
            # this agent cannot avoid the other agent, so the other agent has to resolve the conflict
            # (an idle other agent steps aside to its parking position)
            other_resolves_conflict = True
        elif cost_mine > cost_other:
            other_resolves_conflict = True
        elif cost_mine < cost_other:
            other_resolves_conflict = False
        else:  # cost_mine == cost_other
            other_resolves_conflict = bool(rng.choice([True, False]))
        return other_resolves_conflict

    @staticmethod
    def _karma_payment_rule(
        cost_mine: int, cost_other: int, other_resolves_conflict: bool, karma_params
    ) -> int:
        # RULE 1: fixed payment
        # payment = karma_params["karma_payment"]

        # RULE 2: loser has to avoid collision, winner pays the cost difference between the two agents
        # (i.e. the overall collision avoidance effort that was saved through the negotiation agreement)
        # payment = (
        #     max(0, cost_mine - cost_other)
        #     if other_resolves_conflict
        #     else max(0, cost_other - cost_mine)
        # )

        # RULE 3: loser has to avoid collision, winner pays the collision avoidance effort of the loser
        # (never negative, e.g. when the avoiding route drops waits of the old one)
        payment = max(0, cost_other if other_resolves_conflict else cost_mine)

        # RULE 4: loser has to avoid collision, winner pays the collision avoidance effort they saved through this
        # payment = cost_mine if other_resolves_conflict else cost_other

        return payment

    @staticmethod
    def negotiate_karma(
        cost_other: int,
        cost_mine: int,
        agent_other: Agent,
        agent_self: Agent,
        karma_params,
    ) -> bool:
        # initialize negotiation agreement parameters
        other_resolves_conflict: bool

        # compute cost values considering past behavior (karma balance)
        cost_other_adjusted = (
            cost_other + karma_params["karma_influence"] * agent_other.karma_balance
        )
        cost_mine_adjusted = (
            cost_mine + karma_params["karma_influence"] * agent_self.karma_balance
        )

        if cost_mine == COST_TO_CHANGE_INFEASIBLE:
            # this agent cannot avoid the other agent, so the other agent has to resolve the conflict
            # (an idle other agent steps aside to its parking position)
            other_resolves_conflict = True
        elif agent_other.is_idle():
            # an idle agent has no task to be delayed and does not give way, so this agent has to resolve the conflict
            other_resolves_conflict = False
        elif cost_mine_adjusted - cost_other_adjusted > karma_params["delta_threshold"]:
            # if the agent's own cost is sufficiently higher than the other agent's cost, the other agent has to resolve the conflict
            other_resolves_conflict = True
        elif cost_mine_adjusted - cost_other_adjusted < karma_params["delta_threshold"]:
            # if difference of augmented costs is zero or below threshold, this agent has to resolve the conflict
            other_resolves_conflict = False
        else:
            # if the difference of adjusted costs is below the threshold, we randomize the decision to avoid systematic bias
            other_resolves_conflict = bool(
                agent_self.environment.rng.choice([True, False])
            )

        # if np.isclose(
        #     cost_mine_adjusted - cost_other_adjusted,
        #     karma_params["delta_threshold"],
        #     atol=1e-5,
        # ):
        #     # if the difference of adjusted costs is equal to the threshold (considering numerical tolerances), we randomize the decision to avoid systematic bias
        #     other_resolves_conflict = bool(
        #         agent_self.environment.rng.choice([True, False])
        #     )
        # elif cost_mine_adjusted - cost_other_adjusted > karma_params["delta_threshold"]:
        #     # if the agent's own cost is sufficiently higher than the other agent's cost, the other agent has to resolve the conflict
        #     other_resolves_conflict = True
        # else:
        #     # if difference of augmented costs is below the threshold, this agent has to resolve the conflict
        #     other_resolves_conflict = False

        # idle agents are outside the karma economy: no payment when they block or are forced aside
        if agent_other.is_idle():
            return other_resolves_conflict

        payment = NegotiationStrategy._karma_payment_rule(
            cost_mine,
            cost_other,
            other_resolves_conflict=other_resolves_conflict,
            karma_params=karma_params,
        )
        # karma balances never become negative, so the winner pays at most its balance
        payment = min(
            payment,
            (
                agent_self.karma_balance
                if other_resolves_conflict
                else agent_other.karma_balance
            ),
        )
        if other_resolves_conflict:
            agent_self.karma_balance -= payment
            agent_other.karma_balance += payment
        else:
            agent_self.karma_balance += payment
            agent_other.karma_balance -= payment

        return other_resolves_conflict
