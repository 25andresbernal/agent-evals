from __future__ import annotations

from agent_evals.report import from_json, render_diff, render_markdown, summarize, to_json
from agent_evals.runner import CaseResult, ToolCall
from agent_evals.scorecard import Dimension, Scorecard
from agent_evals.scorers.base import ScoreResult


def make_scorecard() -> Scorecard:
    return Scorecard(
        name="Test Scorecard",
        pass_threshold=0.7,
        dimensions=[
            Dimension(name="task_success", scorer="task_success", weight=0.5, threshold=0.5),
            Dimension(name="cost", scorer="cost", weight=0.5, threshold=0.5),
        ],
    )


def make_result(case_id: str, weighted_score: float, passed: bool) -> CaseResult:
    return CaseResult(
        case_id=case_id,
        input="some input",
        output="some output",
        tags=["tag1"],
        tool_calls=[ToolCall(name="lookup", args={"a": 1})],
        latency_ms=12.5,
        cost_usd=0.001,
        dimension_scores={
            "task_success": ScoreResult(score=weighted_score, passed=passed, detail="detail a"),
            "cost": ScoreResult(score=1.0, passed=True, detail="detail b"),
        },
        weighted_score=weighted_score,
        passed=passed,
    )


def test_summarize_counts_pass_and_fail():
    results = [make_result("c1", 0.9, True), make_result("c2", 0.4, False)]
    summary = summarize(results)
    assert summary.total == 2
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.pass_rate == 0.5


def test_summarize_empty_results():
    summary = summarize([])
    assert summary.total == 0
    assert summary.pass_rate == 0.0


def test_to_json_from_json_round_trip():
    results = [make_result("c1", 0.9, True), make_result("c2", 0.4, False)]
    scorecard = make_scorecard()
    data = to_json(results, scorecard, suite_name="My Suite")
    assert data["suite"] == "My Suite"
    assert data["summary"]["total"] == 2

    restored = from_json(data)
    assert len(restored) == 2
    assert restored[0].case_id == "c1"
    assert restored[0].weighted_score == 0.9
    assert restored[0].dimension_scores["task_success"].score == 0.9
    assert restored[0].tool_calls[0].name == "lookup"


def test_render_markdown_contains_key_sections():
    results = [make_result("c1", 0.9, True), make_result("c2", 0.4, False)]
    md = render_markdown(results, make_scorecard(), suite_name="My Suite")
    assert "# My Suite" in md
    assert "## Summary by dimension" in md
    assert "## Case results" in md
    assert "c1" in md
    assert "c2" in md
    assert "PASS" in md
    assert "FAIL" in md
    assert "## Failed case details" in md


def test_render_markdown_omits_failed_section_when_all_pass():
    results = [make_result("c1", 0.9, True)]
    md = render_markdown(results, make_scorecard())
    assert "## Failed case details" not in md


def test_render_diff_flags_regression():
    old = [make_result("c1", 0.9, True)]
    new = [make_result("c1", 0.4, False)]
    diff = render_diff(old, new)
    assert "REGRESSION" in diff
    assert "1 case(s) regressed" in diff


def test_render_diff_flags_fixed_case():
    old = [make_result("c1", 0.4, False)]
    new = [make_result("c1", 0.9, True)]
    diff = render_diff(old, new)
    assert "fixed" in diff
    assert "No cases regressed" in diff


def test_render_diff_handles_added_and_removed_cases():
    old = [make_result("c1", 0.9, True)]
    new = [make_result("c1", 0.9, True), make_result("c2", 0.9, True)]
    diff = render_diff(old, new)
    assert "added" in diff
