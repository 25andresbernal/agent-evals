"""tool_correctness: did the agent call the right tools with the right
arguments.

Every case in `case.expected_tool_calls` must be matched, in any order, by
one of the agent's actual tool calls: same name, and every key in the
expected call's `args` present with an equal value in the actual call.
Extra keys in the actual call's args are ignored.

By default, extra tool calls the agent made beyond what was expected do not
count against the score. Set `config.strict: true` to require an exact set
of calls with nothing extra.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_evals.scorers.base import ScoreResult

if TYPE_CHECKING:
    from agent_evals.cases import EvalCase, ExpectedToolCall
    from agent_evals.runner import AgentResponse, RunContext, ToolCall


def _matches(expected: ExpectedToolCall, actual: ToolCall) -> bool:
    if expected.name != actual.name:
        return False
    for key, value in expected.args.items():
        if key not in actual.args or actual.args[key] != value:
            return False
    return True


def score_tool_correctness(
    case: EvalCase, response: AgentResponse, config: dict[str, Any], ctx: RunContext
) -> ScoreResult:
    del ctx
    expected_calls = list(case.expected_tool_calls)
    actual_calls = list(response.tool_calls)

    if not expected_calls:
        if config.get("strict") and actual_calls:
            return ScoreResult(
                score=0.0,
                passed=False,
                detail=f"expected no tool calls, got {[c.name for c in actual_calls]}",
            )
        return ScoreResult(score=1.0, passed=True, detail="no tool calls expected")

    remaining = list(actual_calls)
    missing: list[str] = []
    for expected in expected_calls:
        match = next((a for a in remaining if _matches(expected, a)), None)
        if match is None:
            missing.append(expected.name)
        else:
            remaining.remove(match)

    matched_count = len(expected_calls) - len(missing)
    score = matched_count / len(expected_calls)
    extras = [c.name for c in remaining]

    strict = bool(config.get("strict", False))
    passed = not missing and (not strict or not extras)
    if strict and extras and not missing:
        # Extra unexpected calls under strict mode: matched everything
        # required but made unrequested calls too. Penalize but do not
        # zero out the score for what it got right.
        score = matched_count / (len(expected_calls) + len(extras))

    details = []
    if missing:
        details.append(f"missing calls: {missing}")
    if extras:
        details.append(f"unexpected calls: {extras}" + (" (strict mode)" if strict else ""))
    detail = "; ".join(details) if details else "all expected tool calls matched"

    return ScoreResult(score=score, passed=passed, detail=detail)
