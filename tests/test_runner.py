from __future__ import annotations

import pytest

from agent_evals.cases import EvalCase, ExpectedToolCall
from agent_evals.judge.fake_judge import FakeJudge
from agent_evals.runner import AgentResponse, Runner, ToolCall
from agent_evals.scorecard import Dimension, Scorecard


def make_scorecard() -> Scorecard:
    return Scorecard(
        name="Test Scorecard",
        pass_threshold=0.7,
        dimensions=[
            Dimension(name="task_success", scorer="task_success", weight=0.6, threshold=0.5),
            Dimension(
                name="tool_correctness", scorer="tool_correctness", weight=0.4, threshold=0.5
            ),
        ],
    )


def good_agent(message: str) -> AgentResponse:
    return AgentResponse(
        output=f"Handled: {message}",
        tool_calls=[ToolCall(name="lookup", args={"query": message})],
        model="rule-based-v1",
        cost_usd=0.0,
    )


def bad_agent(message: str) -> AgentResponse:
    del message
    return AgentResponse(output="I don't know.", tool_calls=[], model="rule-based-v1", cost_usd=0.0)


def test_runner_scores_a_passing_case():
    case = EvalCase(
        id="c1",
        input="find my order",
        expected_output_contains=["handled"],
        expected_tool_calls=[ExpectedToolCall(name="lookup", args={"query": "find my order"})],
    )
    runner = Runner(agent=good_agent, scorecard=make_scorecard())
    result = runner.run_case(case)
    assert result.passed
    assert result.weighted_score == pytest.approx(1.0)
    assert result.case_id == "c1"
    assert result.cost_usd == 0.0
    assert result.latency_ms >= 0.0


def test_runner_scores_a_failing_case():
    case = EvalCase(
        id="c1",
        input="find my order",
        expected_output_contains=["handled"],
        expected_tool_calls=[ExpectedToolCall(name="lookup", args={})],
    )
    runner = Runner(agent=bad_agent, scorecard=make_scorecard())
    result = runner.run_case(case)
    assert not result.passed
    assert result.weighted_score < 0.7


def test_runner_run_suite_returns_one_result_per_case():
    cases = [
        EvalCase(id="c1", input="a"),
        EvalCase(id="c2", input="b"),
        EvalCase(id="c3", input="c"),
    ]
    runner = Runner(agent=good_agent, scorecard=make_scorecard())
    results = runner.run_suite(cases)
    assert [r.case_id for r in results] == ["c1", "c2", "c3"]


def test_runner_respects_per_dimension_threshold_even_if_average_passes():
    scorecard = Scorecard(
        name="s",
        pass_threshold=0.5,
        dimensions=[
            Dimension(name="task_success", scorer="task_success", weight=0.9, threshold=0.5),
            Dimension(
                name="tool_correctness", scorer="tool_correctness", weight=0.1, threshold=0.9
            ),
        ],
    )
    case = EvalCase(
        id="c1",
        input="hi",
        expected_output_contains=["handled"],
        expected_tool_calls=[ExpectedToolCall(name="missing_tool", args={})],
    )
    runner = Runner(agent=good_agent, scorecard=scorecard)
    result = runner.run_case(case)
    # weighted average is high (task_success dominates) but tool_correctness
    # is 0.0 against a 0.9 threshold, so the case must fail overall.
    assert result.weighted_score >= 0.5
    assert not result.passed


def test_runner_uses_supplied_judge_for_llm_judge_dimension():
    scorecard = Scorecard(
        name="s",
        pass_threshold=0.0,
        dimensions=[Dimension(name="quality", scorer="llm_judge", weight=1.0, threshold=0.0)],
    )
    case = EvalCase(id="c1", input="hi", rubric="rate helpfulness")
    runner = Runner(agent=good_agent, scorecard=scorecard, judge=FakeJudge())
    result = runner.run_case(case)
    assert "quality" in result.dimension_scores
