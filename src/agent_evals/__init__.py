"""agent_evals: a lightweight framework for evaluating LLM agents.

Core concepts:

- `Scorecard`: weighted dimensions with pass thresholds, defined in YAML.
- `EvalCase`: one input, its expected outcome, expected tool calls, and tags.
- `Runner`: executes an agent callable against a set of cases and scores it.
- `Report`: renders Markdown and JSON reports, and diffs two runs.
"""

from agent_evals.cases import EvalCase, ExpectedToolCall, load_cases
from agent_evals.runner import AgentResponse, CaseResult, Runner, ToolCall
from agent_evals.scorecard import Dimension, Scorecard

__all__ = [
    "AgentResponse",
    "CaseResult",
    "Dimension",
    "EvalCase",
    "ExpectedToolCall",
    "Runner",
    "Scorecard",
    "ToolCall",
    "load_cases",
]

__version__ = "0.1.0"
