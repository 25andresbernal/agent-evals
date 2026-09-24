"""FakeJudge: a deterministic, offline stand-in for a real LLM judge."""

from __future__ import annotations

from agent_evals.judge.base import JudgeResult

FAILURE_MARKERS = ("error", "undefined", "todo", "not implemented", "traceback")


class FakeJudge:
    """A deterministic, offline judge used by tests and by the example eval
    suite when no `ANTHROPIC_API_KEY` is set.

    It does not read the rubric the way a real judge would. It scores by
    simple, explainable heuristics: it rewards a non-empty, reasonably sized
    response that shares vocabulary with the input, and penalizes obvious
    failure markers. This makes runs reproducible without a network call or
    a paid key, which is required for the test suite and the quick start.
    Swap in `AnthropicJudge` for real quality scoring.
    """

    def judge(self, input: str, output: str, rubric: str) -> JudgeResult:
        del rubric

        if not output or not output.strip():
            return JudgeResult(score=0.0, reasoning="output is empty")

        lowered = output.lower()
        for marker in FAILURE_MARKERS:
            if marker in lowered:
                return JudgeResult(
                    score=0.1, reasoning=f"output contains failure marker '{marker}'"
                )

        word_count = len(output.split())
        if word_count < 3:
            length_score = 0.4
        elif word_count > 120:
            length_score = 0.6
        else:
            length_score = 1.0

        input_words = set(input.lower().split())
        output_words = set(lowered.split())
        overlap = len(input_words & output_words)
        relevance_score = min(1.0, 0.6 + 0.1 * overlap)

        score = round(0.5 * length_score + 0.5 * relevance_score, 2)
        return JudgeResult(
            score=score,
            reasoning=f"length_score={length_score}, relevance_score={round(relevance_score, 2)}",
        )
