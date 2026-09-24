"""llm_judge: a rubric-based quality score from an LLM judge.

The rubric comes from `case.rubric` if the case sets one, otherwise from
`config.rubric`. At least one of the two must be set. The judge itself is
supplied on the run context, not configured here, so the same scorecard can
run against `FakeJudge` in CI and `AnthropicJudge` in a real evaluation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_evals.scorers.base import ScoreResult

if TYPE_CHECKING:
    from agent_evals.cases import EvalCase
    from agent_evals.runner import AgentResponse, RunContext


def score_llm_judge(
    case: EvalCase, response: AgentResponse, config: dict[str, Any], ctx: RunContext
) -> ScoreResult:
    if ctx.judge is None:
        raise ValueError(
            "the llm_judge scorer requires a judge; pass one to Runner(judge=...) "
            "(FakeJudge is a good default when no API key is set)"
        )

    rubric = case.rubric or config.get("rubric")
    if not rubric:
        raise ValueError(
            f"case '{case.id}' uses the llm_judge scorer but sets no rubric and the "
            "dimension config sets no default rubric"
        )

    result = ctx.judge.judge(input=case.input, output=response.output, rubric=rubric)
    threshold = float(config.get("threshold", 0.0))
    return ScoreResult(
        score=result.score, passed=result.score >= threshold, detail=result.reasoning
    )
