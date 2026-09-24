from __future__ import annotations

import pytest

from agent_evals.cases import EvalCase, ExpectedToolCall
from agent_evals.pricing import DEFAULT_PRICING
from agent_evals.runner import AgentResponse, RunContext, ToolCall


@pytest.fixture
def simple_case() -> EvalCase:
    return EvalCase(
        id="case-1",
        input="What is your refund policy?",
        expected_output_contains=["refund", "policy"],
        expected_tool_calls=[ExpectedToolCall(name="lookup_policy", args={"topic": "refund"})],
    )


@pytest.fixture
def matching_response() -> AgentResponse:
    return AgentResponse(
        output="Our refund policy allows returns within 30 days.",
        tool_calls=[ToolCall(name="lookup_policy", args={"topic": "refund", "extra": "ignored"})],
        input_tokens=10,
        output_tokens=8,
        model="claude-sonnet-5",
    )


@pytest.fixture
def run_context() -> RunContext:
    return RunContext(latency_ms=5.0, pricing=DEFAULT_PRICING, judge=None)
