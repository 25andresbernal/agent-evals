"""cost: did the agent stay within a per-case cost budget.

`config.max_cost_usd` sets the budget (default 0.01). A case at or under
budget scores 1.0. Score decays linearly to 0.0 as cost reaches double the
budget, and floors at 0.0 beyond that, so a slightly over-budget case is not
scored the same as a wildly over-budget one.

Cost itself comes from `response.cost_usd` when the agent set it directly,
otherwise it is estimated from token counts against the pricing table on
the run context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_evals.pricing import resolve_cost
from agent_evals.scorers.base import ScoreResult

if TYPE_CHECKING:
    from agent_evals.cases import EvalCase
    from agent_evals.runner import AgentResponse, RunContext

DEFAULT_MAX_COST_USD = 0.01


def score_cost(
    case: EvalCase, response: AgentResponse, config: dict[str, Any], ctx: RunContext
) -> ScoreResult:
    del case
    max_cost = float(config.get("max_cost_usd", DEFAULT_MAX_COST_USD))
    cost = resolve_cost(response, ctx.pricing)

    if cost <= max_cost:
        score = 1.0
    elif cost >= max_cost * 2:
        score = 0.0
    else:
        score = 1.0 - (cost - max_cost) / max_cost

    passed = cost <= max_cost
    return ScoreResult(
        score=round(score, 4),
        passed=passed,
        detail=f"cost ${cost:.5f} against budget ${max_cost:.5f}",
    )
