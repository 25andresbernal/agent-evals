from __future__ import annotations

from pathlib import Path

import pytest

from agent_evals.suite import load_suite, resolve_agent


def write_suite(tmp_path: Path) -> Path:
    (tmp_path / "agent.py").write_text(
        """
from agent_evals import AgentResponse

def run_agent(message):
    return AgentResponse(output=f"echo: {message}")
""".strip()
    )
    (tmp_path / "scorecard.yaml").write_text(
        """
name: Test
pass_threshold: 0.5
dimensions:
  - name: task_success
    scorer: task_success
    weight: 1.0
    threshold: 0.5
""".strip()
    )
    (tmp_path / "cases.yaml").write_text(
        """
- id: c1
  input: "hi"
  expected_output_contains: ["echo"]
""".strip()
    )
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        """
name: Test Suite
agent: agent.py:run_agent
scorecard: scorecard.yaml
cases: cases.yaml
judge: fake
""".strip()
    )
    return suite_path


def test_load_suite_resolves_paths_relative_to_suite_file(tmp_path):
    suite_path = write_suite(tmp_path)
    suite = load_suite(suite_path)
    assert suite.name == "Test Suite"
    assert suite.scorecard.name == "Test"
    assert len(suite.cases) == 1
    assert suite.judge_kind == "fake"


def test_load_suite_agent_is_callable(tmp_path):
    suite_path = write_suite(tmp_path)
    suite = load_suite(suite_path)
    agent = suite.load_agent()
    response = agent("hello")
    assert response.output == "echo: hello"


def test_load_suite_missing_required_field(tmp_path):
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text("name: Bad Suite\n")
    with pytest.raises(ValueError, match="agent"):
        load_suite(suite_path)


def test_resolve_agent_from_file_path(tmp_path):
    (tmp_path / "agent.py").write_text(
        """
from agent_evals import AgentResponse

def run_agent(message):
    return AgentResponse(output=message.upper())
""".strip()
    )
    agent = resolve_agent("agent.py:run_agent", tmp_path)
    assert agent("hi").output == "HI"


def test_resolve_agent_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_agent("does_not_exist.py:run_agent", tmp_path)


def test_resolve_agent_invalid_spec_raises(tmp_path):
    with pytest.raises(ValueError, match="invalid agent spec"):
        resolve_agent("no_colon_here", tmp_path)


def test_resolve_agent_from_dotted_module_path():
    agent = resolve_agent("agent_evals.judge.fake_judge:FakeJudge", Path("."))
    assert agent is not None
