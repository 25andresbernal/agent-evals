"""Shared scorer types and the scorer registry."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from agent_evals.cases import EvalCase
    from agent_evals.runner import AgentResponse, RunContext


@dataclass
class ScoreResult:
    """The outcome of scoring one dimension for one case.

    `score` is always normalized to 0.0-1.0 so dimensions can be combined
    into a weighted average regardless of what each scorer measures.
    `passed` reflects the scorer's own judgment where that is meaningful
    (for example, tool_correctness knows what an exact match looks like);
    the report uses the scorecard's per-dimension threshold as the
    authoritative pass/fail line, not this field.
    """

    score: float
    passed: bool
    detail: str = ""


class ScorerFn(Protocol):
    def __call__(
        self,
        case: EvalCase,
        response: AgentResponse,
        config: dict[str, Any],
        ctx: RunContext,
    ) -> ScoreResult: ...


_BUILTIN_SCORERS: dict[str, str] = {
    "task_success": "agent_evals.scorers.task_success:score_task_success",
    "tool_correctness": "agent_evals.scorers.tool_correctness:score_tool_correctness",
    "cost": "agent_evals.scorers.cost:score_cost",
    "latency": "agent_evals.scorers.latency:score_latency",
    "llm_judge": "agent_evals.scorers.llm_judge:score_llm_judge",
}


def resolve_scorer(name: str) -> ScorerFn:
    """Resolve a scorer name to a callable.

    Built-in names (task_success, tool_correctness, cost, latency,
    llm_judge) are resolved from the registry above. Anything else is
    treated as a `module:function` import path, so a team can plug in a
    custom scorer without forking this package.
    """
    target = _BUILTIN_SCORERS.get(name, name)
    if ":" not in target:
        raise ValueError(
            f"unknown scorer '{name}': not a built-in scorer and not a 'module:function' path"
        )
    module_name, func_name = target.rsplit(":", 1)
    module = importlib.import_module(module_name)
    try:
        return getattr(module, func_name)
    except AttributeError as exc:
        raise ValueError(f"scorer '{name}' resolved to {target}, which does not exist") from exc
