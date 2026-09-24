"""Provider-agnostic LLM judge interface.

A judge scores one case's output against a rubric written in plain English.
Any implementation, backed by any provider, only needs to satisfy this
protocol so `agent_evals` never depends on a specific SDK for the core
package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class JudgeResult:
    """The judge's verdict on one case."""

    score: float
    """A score from 0.0 to 1.0 against the rubric."""

    reasoning: str = ""
    """A short explanation, useful when a human reviews judge disagreement."""


@runtime_checkable
class Judge(Protocol):
    """Anything with a `judge` method matching this signature can be used
    as the `llm_judge` scorer's judge."""

    def judge(self, input: str, output: str, rubric: str) -> JudgeResult: ...
