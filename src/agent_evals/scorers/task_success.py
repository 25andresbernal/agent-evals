"""task_success: did the agent produce the right outcome.

Three modes, set via the dimension's `config.mode`:

- `exact` (default when `expected_output` is set): the output must equal
  `case.expected_output` after stripping whitespace.
- `contains` (default otherwise): every string in
  `case.expected_output_contains` must appear in the output, case
  insensitive.
- `custom`: `config.func` is a `module:function` path to a callable
  `(case, response) -> bool`.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from agent_evals.scorers.base import ScoreResult

if TYPE_CHECKING:
    from agent_evals.cases import EvalCase
    from agent_evals.runner import AgentResponse, RunContext


def score_task_success(
    case: EvalCase, response: AgentResponse, config: dict[str, Any], ctx: RunContext
) -> ScoreResult:
    del ctx
    mode = config.get("mode")
    if mode is None:
        mode = "exact" if case.expected_output is not None else "contains"

    if mode == "exact":
        if case.expected_output is None:
            raise ValueError(
                f"case '{case.id}' uses task_success mode 'exact' but sets no expected_output"
            )
        ok = response.output.strip() == case.expected_output.strip()
        detail = (
            "output matched expected_output exactly"
            if ok
            else "output did not match expected_output"
        )
        return ScoreResult(score=1.0 if ok else 0.0, passed=ok, detail=detail)

    if mode == "contains":
        terms = case.expected_output_contains
        if not terms:
            return ScoreResult(
                score=1.0, passed=True, detail="no expected_output_contains terms set"
            )
        lowered = response.output.lower()
        missing = [t for t in terms if t.lower() not in lowered]
        score = (len(terms) - len(missing)) / len(terms)
        ok = not missing
        detail = "all expected terms present" if ok else f"missing terms: {missing}"
        return ScoreResult(score=score, passed=ok, detail=detail)

    if mode == "custom":
        func_path = config.get("func")
        if not func_path:
            raise ValueError(
                f"case '{case.id}' uses task_success mode 'custom' but sets no config.func"
            )
        module_name, func_name = func_path.rsplit(":", 1)
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        ok = bool(func(case, response))
        return ScoreResult(score=1.0 if ok else 0.0, passed=ok, detail=f"custom scorer {func_path}")

    raise ValueError(f"unknown task_success mode '{mode}'")
