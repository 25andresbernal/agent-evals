"""Runner: executes an agent callable against eval cases and scores it.

The agent interface is deliberately minimal: a plain Python callable that
takes the case input string and returns an `AgentResponse`. Any agent, rule
based, a thin wrapper around an API, or a full agent framework, can be
plugged in by writing a few lines of adapter code with that shape.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agent_evals.cases import EvalCase
from agent_evals.judge.base import Judge
from agent_evals.pricing import DEFAULT_PRICING, resolve_cost
from agent_evals.scorecard import Scorecard
from agent_evals.scorers import ScoreResult, resolve_scorer


@dataclass
class ToolCall:
    """A single tool call, as made by an agent or expected by a case."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """What an agent callable returns for one case.

    `cost_usd`, when set, overrides the cost computed from token counts and
    the pricing table. Leave it unset to let the cost scorer estimate cost
    from `model`, `input_tokens`, and `output_tokens`.
    """

    output: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str | None = None
    cost_usd: float | None = None


Agent = Callable[[str], AgentResponse]
"""The agent interface: any callable with this signature can be evaluated."""


@dataclass
class RunContext:
    """Shared state a scorer may need beyond the case and the response."""

    latency_ms: float
    pricing: dict[str, dict[str, float]]
    judge: Judge | None


@dataclass
class CaseResult:
    """The full scoring outcome for one case."""

    case_id: str
    input: str
    output: str
    tags: list[str]
    tool_calls: list[ToolCall]
    latency_ms: float
    cost_usd: float
    dimension_scores: dict[str, ScoreResult]
    weighted_score: float
    passed: bool


class Runner:
    """Runs an agent against a set of cases and scores each one against a
    scorecard."""

    def __init__(
        self,
        agent: Agent,
        scorecard: Scorecard,
        judge: Judge | None = None,
        pricing: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self.agent = agent
        self.scorecard = scorecard
        self.judge = judge
        self.pricing = pricing if pricing is not None else DEFAULT_PRICING

    def run_case(self, case: EvalCase) -> CaseResult:
        start = time.perf_counter()
        response = self.agent(case.input)
        latency_ms = (time.perf_counter() - start) * 1000

        cost_usd = resolve_cost(response, self.pricing)

        ctx = RunContext(latency_ms=latency_ms, pricing=self.pricing, judge=self.judge)

        dimension_scores: dict[str, ScoreResult] = {}
        for dimension in self.scorecard.dimensions:
            scorer_fn = resolve_scorer(dimension.scorer)
            dimension_scores[dimension.name] = scorer_fn(case, response, dimension.config, ctx)

        weighted_score = self.scorecard.weighted_score(
            {name: result.score for name, result in dimension_scores.items()}
        )
        meets_dimension_thresholds = all(
            dimension_scores[d.name].score >= d.threshold for d in self.scorecard.dimensions
        )
        passed = weighted_score >= self.scorecard.pass_threshold and meets_dimension_thresholds

        return CaseResult(
            case_id=case.id,
            input=case.input,
            output=response.output,
            tags=case.tags,
            tool_calls=response.tool_calls,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            dimension_scores=dimension_scores,
            weighted_score=weighted_score,
            passed=passed,
        )

    def run_suite(self, cases: list[EvalCase]) -> list[CaseResult]:
        return [self.run_case(case) for case in cases]
