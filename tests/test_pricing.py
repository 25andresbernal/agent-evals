from __future__ import annotations

from agent_evals.pricing import compute_cost, resolve_cost
from agent_evals.runner import AgentResponse


def test_compute_cost_known_model():
    cost = compute_cost("claude-sonnet-5", input_tokens=1000, output_tokens=1000)
    assert cost > 0


def test_compute_cost_unknown_model_returns_zero():
    assert compute_cost("not-a-real-model", input_tokens=1000, output_tokens=1000) == 0.0


def test_resolve_cost_prefers_explicit_cost_usd():
    response = AgentResponse(output="ok", cost_usd=0.5, model="claude-sonnet-5", input_tokens=1000)
    assert resolve_cost(response) == 0.5


def test_resolve_cost_estimates_from_tokens_when_unset():
    response = AgentResponse(
        output="ok", model="claude-sonnet-5", input_tokens=1000, output_tokens=1000
    )
    assert resolve_cost(response) > 0
