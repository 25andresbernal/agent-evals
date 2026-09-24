"""A small, editable pricing table used by the cost scorer.

Prices are USD per 1,000 tokens. This table is deliberately not exhaustive
and not guaranteed current: pass your own table to `Runner` or the CLI
config when prices change or you use a model that is not listed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_evals.runner import AgentResponse

DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-5": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-haiku-4.5": {"input_per_1k": 0.001, "output_per_1k": 0.005},
    "claude-opus-4.5": {"input_per_1k": 0.015, "output_per_1k": 0.075},
    "gpt-4o": {"input_per_1k": 0.0025, "output_per_1k": 0.01},
    "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    # A rule-based or otherwise non-LLM agent makes no model call, so it has
    # no per-token cost. This entry exists so the example agent can be
    # scored on cost without every case needing an explicit override.
    "rule-based-v1": {"input_per_1k": 0.0, "output_per_1k": 0.0},
}


def compute_cost(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    pricing: dict[str, dict[str, float]] | None = None,
) -> float:
    """Compute USD cost from token counts using a pricing table.

    Returns 0.0 for an unrecognized or missing model rather than raising, so
    a scorer can always produce a number. Use an explicit `cost_usd` on the
    `AgentResponse` when you need an exact, non-estimated figure.
    """
    table = pricing if pricing is not None else DEFAULT_PRICING
    rates = table.get(model or "")
    if rates is None:
        return 0.0
    return (input_tokens / 1000) * rates["input_per_1k"] + (output_tokens / 1000) * rates[
        "output_per_1k"
    ]


def resolve_cost(
    response: AgentResponse, pricing: dict[str, dict[str, float]] | None = None
) -> float:
    """Return the cost to attribute to a response.

    Uses `response.cost_usd` when the agent supplied one directly, since
    that is the most accurate figure available. Otherwise estimates it from
    token counts and the pricing table.
    """
    if response.cost_usd is not None:
        return response.cost_usd
    return compute_cost(response.model, response.input_tokens, response.output_tokens, pricing)
