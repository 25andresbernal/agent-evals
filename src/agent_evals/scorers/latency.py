"""latency: did the agent respond within a per-case time budget.

`config.max_latency_ms` sets the budget (default 2000ms). Same decay curve
as the cost scorer: 1.0 at or under budget, linear decay to 0.0 at double
budget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_evals.scorers.base import ScoreResult

if TYPE_CHECKING:
    from agent_evals.cases import EvalCase
    from agent_evals.runner import AgentResponse, RunContext

DEFAULT_MAX_LATENCY_MS = 2000.0


def score_latency(
    case: EvalCase, response: AgentResponse, config: dict[str, Any], ctx: RunContext
) -> ScoreResult:
    del case, response
    max_latency = float(config.get("max_latency_ms", DEFAULT_MAX_LATENCY_MS))
    latency = ctx.latency_ms

    if latency <= max_latency:
        score = 1.0
    elif latency >= max_latency * 2:
        score = 0.0
    else:
        score = 1.0 - (latency - max_latency) / max_latency

    passed = latency <= max_latency
    return ScoreResult(
        score=round(score, 4),
        passed=passed,
        detail=f"latency {latency:.1f}ms against budget {max_latency:.1f}ms",
    )
