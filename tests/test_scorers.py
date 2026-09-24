from __future__ import annotations

import pytest

from agent_evals.cases import EvalCase, ExpectedToolCall
from agent_evals.judge.fake_judge import FakeJudge
from agent_evals.runner import AgentResponse, RunContext, ToolCall
from agent_evals.scorers.base import resolve_scorer
from agent_evals.scorers.cost import score_cost
from agent_evals.scorers.latency import score_latency
from agent_evals.scorers.llm_judge import score_llm_judge
from agent_evals.scorers.task_success import score_task_success
from agent_evals.scorers.tool_correctness import score_tool_correctness

# --- task_success -----------------------------------------------------


def test_task_success_contains_all_present():
    case = EvalCase(id="c1", input="hi", expected_output_contains=["hello", "world"])
    response = AgentResponse(output="hello there, world!")
    result = score_task_success(case, response, {}, ctx=None)
    assert result.score == 1.0
    assert result.passed


def test_task_success_contains_partial_match():
    case = EvalCase(id="c1", input="hi", expected_output_contains=["hello", "world"])
    response = AgentResponse(output="hello there")
    result = score_task_success(case, response, {}, ctx=None)
    assert result.score == pytest.approx(0.5)
    assert not result.passed


def test_task_success_exact_match():
    case = EvalCase(id="c1", input="hi", expected_output="hello")
    response = AgentResponse(output="hello")
    result = score_task_success(case, response, {"mode": "exact"}, ctx=None)
    assert result.score == 1.0


def test_task_success_exact_mismatch():
    case = EvalCase(id="c1", input="hi", expected_output="hello")
    response = AgentResponse(output="goodbye")
    result = score_task_success(case, response, {"mode": "exact"}, ctx=None)
    assert result.score == 0.0
    assert not result.passed


def test_task_success_custom_mode():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="hello")
    config = {"mode": "custom", "func": "tests.test_scorers:_always_true"}
    result = score_task_success(case, response, config, ctx=None)
    assert result.score == 1.0


def _always_true(case, response):
    return True


def test_task_success_no_expected_terms_defaults_to_pass():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="anything")
    result = score_task_success(case, response, {}, ctx=None)
    assert result.score == 1.0


# --- tool_correctness ---------------------------------------------------


def test_tool_correctness_exact_match():
    case = EvalCase(
        id="c1",
        input="hi",
        expected_tool_calls=[ExpectedToolCall(name="lookup", args={"id": 1})],
    )
    response = AgentResponse(output="ok", tool_calls=[ToolCall(name="lookup", args={"id": 1})])
    result = score_tool_correctness(case, response, {}, ctx=None)
    assert result.score == 1.0
    assert result.passed


def test_tool_correctness_extra_args_ignored():
    case = EvalCase(
        id="c1",
        input="hi",
        expected_tool_calls=[ExpectedToolCall(name="lookup", args={"id": 1})],
    )
    response = AgentResponse(
        output="ok", tool_calls=[ToolCall(name="lookup", args={"id": 1, "extra": "x"})]
    )
    result = score_tool_correctness(case, response, {}, ctx=None)
    assert result.score == 1.0


def test_tool_correctness_missing_call():
    case = EvalCase(
        id="c1", input="hi", expected_tool_calls=[ExpectedToolCall(name="lookup", args={})]
    )
    response = AgentResponse(output="ok", tool_calls=[])
    result = score_tool_correctness(case, response, {}, ctx=None)
    assert result.score == 0.0
    assert not result.passed
    assert "missing" in result.detail


def test_tool_correctness_wrong_arg_value_counts_as_missing():
    case = EvalCase(
        id="c1", input="hi", expected_tool_calls=[ExpectedToolCall(name="lookup", args={"id": 1})]
    )
    response = AgentResponse(output="ok", tool_calls=[ToolCall(name="lookup", args={"id": 2})])
    result = score_tool_correctness(case, response, {}, ctx=None)
    assert result.score == 0.0


def test_tool_correctness_partial_credit_for_multiple_expected_calls():
    case = EvalCase(
        id="c1",
        input="hi",
        expected_tool_calls=[
            ExpectedToolCall(name="lookup", args={}),
            ExpectedToolCall(name="notify", args={}),
        ],
    )
    response = AgentResponse(output="ok", tool_calls=[ToolCall(name="lookup", args={})])
    result = score_tool_correctness(case, response, {}, ctx=None)
    assert result.score == pytest.approx(0.5)


def test_tool_correctness_no_expected_calls_passes_by_default():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok", tool_calls=[ToolCall(name="lookup", args={})])
    result = score_tool_correctness(case, response, {}, ctx=None)
    assert result.score == 1.0


def test_tool_correctness_strict_mode_penalizes_extra_calls():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok", tool_calls=[ToolCall(name="lookup", args={})])
    result = score_tool_correctness(case, response, {"strict": True}, ctx=None)
    assert result.score == 0.0
    assert not result.passed


# --- cost -----------------------------------------------------------------


def test_cost_within_budget_scores_full(run_context):
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok", cost_usd=0.001)
    result = score_cost(case, response, {"max_cost_usd": 0.01}, run_context)
    assert result.score == 1.0
    assert result.passed


def test_cost_over_budget_decays(run_context):
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok", cost_usd=0.015)
    result = score_cost(case, response, {"max_cost_usd": 0.01}, run_context)
    assert 0.0 < result.score < 1.0
    assert not result.passed


def test_cost_far_over_budget_floors_at_zero(run_context):
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok", cost_usd=1.0)
    result = score_cost(case, response, {"max_cost_usd": 0.01}, run_context)
    assert result.score == 0.0


def test_cost_estimated_from_tokens_when_not_set(run_context):
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(
        output="ok", model="rule-based-v1", input_tokens=100, output_tokens=100
    )
    result = score_cost(case, response, {}, run_context)
    assert result.score == 1.0  # rule-based-v1 is priced at $0


# --- latency ----------------------------------------------------------


def test_latency_within_budget():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok")
    ctx = RunContext(latency_ms=50.0, pricing={}, judge=None)
    result = score_latency(case, response, {"max_latency_ms": 100.0}, ctx)
    assert result.score == 1.0


def test_latency_over_budget_decays():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok")
    ctx = RunContext(latency_ms=150.0, pricing={}, judge=None)
    result = score_latency(case, response, {"max_latency_ms": 100.0}, ctx)
    assert 0.0 < result.score < 1.0
    assert not result.passed


# --- llm_judge ----------------------------------------------------------


def test_llm_judge_uses_fake_judge():
    case = EvalCase(id="c1", input="What is the weather?", rubric="Rate helpfulness 0 to 1.")
    response = AgentResponse(output="It is sunny and 75 degrees today.")
    ctx = RunContext(latency_ms=0.0, pricing={}, judge=FakeJudge())
    result = score_llm_judge(case, response, {}, ctx)
    assert 0.0 <= result.score <= 1.0


def test_llm_judge_requires_a_judge():
    case = EvalCase(id="c1", input="hi", rubric="rate it")
    response = AgentResponse(output="ok")
    ctx = RunContext(latency_ms=0.0, pricing={}, judge=None)
    with pytest.raises(ValueError, match="judge"):
        score_llm_judge(case, response, {}, ctx)


def test_llm_judge_requires_a_rubric():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="ok")
    ctx = RunContext(latency_ms=0.0, pricing={}, judge=FakeJudge())
    with pytest.raises(ValueError, match="rubric"):
        score_llm_judge(case, response, {}, ctx)


def test_llm_judge_falls_back_to_config_rubric():
    case = EvalCase(id="c1", input="hi")
    response = AgentResponse(output="A reasonably helpful and complete answer to the question.")
    ctx = RunContext(latency_ms=0.0, pricing={}, judge=FakeJudge())
    result = score_llm_judge(case, response, {"rubric": "rate it"}, ctx)
    assert result.score > 0.0


# --- FakeJudge --------------------------------------------------------


def test_fake_judge_empty_output_scores_zero():
    result = FakeJudge().judge(input="hi", output="", rubric="rate it")
    assert result.score == 0.0


def test_fake_judge_failure_marker_scores_low():
    result = FakeJudge().judge(input="hi", output="Traceback: undefined error", rubric="rate it")
    assert result.score <= 0.2


def test_fake_judge_is_deterministic():
    j = FakeJudge()
    r1 = j.judge(input="hello there", output="hello, how can I help you today?", rubric="r")
    r2 = j.judge(input="hello there", output="hello, how can I help you today?", rubric="r")
    assert r1.score == r2.score


# --- resolve_scorer -----------------------------------------------------


def test_resolve_scorer_builtin_names():
    for name in ("task_success", "tool_correctness", "cost", "latency", "llm_judge"):
        fn = resolve_scorer(name)
        assert callable(fn)


def test_resolve_scorer_unknown_name_raises():
    with pytest.raises(ValueError):
        resolve_scorer("not_a_real_scorer")


def test_resolve_scorer_custom_module_path():
    fn = resolve_scorer("tests.test_scorers:_always_true")
    assert fn(None, None) is True
