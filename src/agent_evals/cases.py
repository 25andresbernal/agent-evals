"""EvalCase: a single input, its expected outcome, and the tool calls a
correct agent should make.

Cases are usually authored in YAML by whoever owns the eval, often a PM,
because the file only needs the inputs and expectations, not a programming
model of the agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ExpectedToolCall:
    """A tool call an agent is expected to make for a case.

    `args` is an optional subset match: every key present in `args` must
    appear in the actual call with an equal value. Keys the agent adds that
    are not listed here are ignored. Leave `args` empty to only check that
    the tool was called, regardless of arguments.
    """

    name: str
    args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpectedToolCall:
        return cls(name=data["name"], args=data.get("args") or {})


@dataclass
class EvalCase:
    """One eval case: an input and what a correct agent response looks like."""

    id: str
    input: str
    tags: list[str] = field(default_factory=list)
    expected_output: str | None = None
    expected_output_contains: list[str] = field(default_factory=list)
    expected_tool_calls: list[ExpectedToolCall] = field(default_factory=list)
    rubric: str | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalCase:
        if "id" not in data:
            raise ValueError("eval case is missing required field 'id'")
        if "input" not in data:
            raise ValueError(f"eval case '{data['id']}' is missing required field 'input'")

        expected_output_contains = data.get("expected_output_contains") or []
        if isinstance(expected_output_contains, str):
            expected_output_contains = [expected_output_contains]

        expected_tool_calls = [
            ExpectedToolCall.from_dict(item) for item in data.get("expected_tool_calls") or []
        ]

        return cls(
            id=str(data["id"]),
            input=str(data["input"]),
            tags=list(data.get("tags") or []),
            expected_output=data.get("expected_output"),
            expected_output_contains=list(expected_output_contains),
            expected_tool_calls=expected_tool_calls,
            rubric=data.get("rubric"),
            notes=data.get("notes"),
        )


def load_cases(path: str | Path) -> list[EvalCase]:
    """Load eval cases from a YAML file.

    Accepts either a top-level list of cases, or a mapping with a `cases`
    key, so a suite author can keep a title or shared metadata alongside the
    cases if they want to.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"{path} is empty")

    if isinstance(data, dict):
        raw_cases = data.get("cases")
        if raw_cases is None:
            raise ValueError(f"{path} has no top-level list and no 'cases' key")
    elif isinstance(data, list):
        raw_cases = data
    else:
        raise ValueError(f"{path} must contain a list of cases or a mapping with a 'cases' key")

    cases = [EvalCase.from_dict(item) for item in raw_cases]

    seen_ids = set()
    for case in cases:
        if case.id in seen_ids:
            raise ValueError(f"duplicate case id '{case.id}' in {path}")
        seen_ids.add(case.id)

    return cases
