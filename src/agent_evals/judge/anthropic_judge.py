"""AnthropicJudge: an LLM judge backed by the Anthropic API.

Requires the `anthropic` package (`pip install "agent-evals[anthropic]"`)
and an `ANTHROPIC_API_KEY`. Neither is required to import `agent_evals` or
to run its test suite: the import happens lazily inside `__init__` so a
user who only wants `FakeJudge` never needs the SDK installed.
"""

from __future__ import annotations

import json
import os
import re

from agent_evals.judge.base import JudgeResult

DEFAULT_MODEL = "claude-sonnet-5"

JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator scoring one response from an AI agent
against a rubric a product manager wrote. Read the input the agent received, the rubric, and the
agent's output. Return your verdict as a single JSON object with exactly two keys: "score", a
number from 0.0 to 1.0, and "reasoning", one or two sentences explaining the score. Return only
the JSON object, no other text."""

JUDGE_USER_TEMPLATE = """Rubric:
{rubric}

Input the agent received:
{input}

Agent's output:
{output}"""


class AnthropicJudge:
    """Scores case output with a Claude model, given a plain-English rubric."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ImportError(
                "AnthropicJudge requires the 'anthropic' package. "
                "Install it with: pip install 'agent-evals[anthropic]'"
            ) from exc

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "AnthropicJudge needs an API key. Set ANTHROPIC_API_KEY or pass api_key=."
            )

        self.model = model
        self._client = anthropic.Anthropic(api_key=key)

    def judge(self, input: str, output: str, rubric: str) -> JudgeResult:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=300,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": JUDGE_USER_TEMPLATE.format(
                        rubric=rubric, input=input, output=output
                    ),
                }
            ],
        )
        text = "".join(block.text for block in message.content if hasattr(block, "text"))
        return _parse_judge_response(text)


def _parse_judge_response(text: str) -> JudgeResult:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"could not find a JSON object in judge response: {text!r}")
    data = json.loads(match.group(0))
    score = max(0.0, min(1.0, float(data["score"])))
    return JudgeResult(score=score, reasoning=str(data.get("reasoning", "")))
