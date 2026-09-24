from __future__ import annotations

import pytest

from agent_evals.judge.anthropic_judge import _parse_judge_response


def test_parse_judge_response_extracts_json():
    text = '{"score": 0.8, "reasoning": "Clear and helpful."}'
    result = _parse_judge_response(text)
    assert result.score == 0.8
    assert result.reasoning == "Clear and helpful."


def test_parse_judge_response_extracts_json_with_surrounding_text():
    text = 'Here is my verdict:\n{"score": 1.0, "reasoning": "Perfect."}\nThanks.'
    result = _parse_judge_response(text)
    assert result.score == 1.0


def test_parse_judge_response_clamps_score_to_valid_range():
    text = '{"score": 1.5, "reasoning": "too high"}'
    result = _parse_judge_response(text)
    assert result.score == 1.0


def test_parse_judge_response_raises_without_json():
    with pytest.raises(ValueError, match="JSON"):
        _parse_judge_response("no json here at all")


def test_anthropic_judge_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from agent_evals.judge.anthropic_judge import AnthropicJudge

    with pytest.raises(ValueError, match="API key"):
        AnthropicJudge()
