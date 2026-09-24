from __future__ import annotations

import json
from pathlib import Path

from agent_evals.cli import main


def write_suite(tmp_path: Path, pass_threshold: float = 0.5) -> Path:
    (tmp_path / "agent.py").write_text(
        """
from agent_evals import AgentResponse

def run_agent(message):
    return AgentResponse(output=f"echo: {message}", model="rule-based-v1", cost_usd=0.0)
""".strip()
    )
    (tmp_path / "scorecard.yaml").write_text(
        f"""
name: Test
pass_threshold: {pass_threshold}
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


def test_cli_run_writes_markdown_and_json(tmp_path):
    suite_path = write_suite(tmp_path)
    out_path = tmp_path / "report.md"
    json_path = tmp_path / "run.json"

    exit_code = main(["run", str(suite_path), "--out", str(out_path), "--json", str(json_path)])

    assert exit_code == 0
    assert out_path.exists()
    assert "Test Suite" in out_path.read_text()
    data = json.loads(json_path.read_text())
    assert data["summary"]["total"] == 1


def test_cli_run_fail_under_exits_nonzero(tmp_path):
    # task_success will fail because "echo" is not the expected term.
    suite_path = tmp_path / "suite.yaml"
    (tmp_path / "agent.py").write_text(
        """
from agent_evals import AgentResponse

def run_agent(message):
    return AgentResponse(output="nope", model="rule-based-v1", cost_usd=0.0)
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
    suite_path.write_text(
        """
name: Test Suite
agent: agent.py:run_agent
scorecard: scorecard.yaml
cases: cases.yaml
judge: fake
""".strip()
    )

    exit_code = main(
        [
            "run",
            str(suite_path),
            "--out",
            str(tmp_path / "report.md"),
            "--fail-under",
            "0.9",
        ]
    )
    assert exit_code == 1


def test_cli_compare_writes_diff(tmp_path):
    suite_path = write_suite(tmp_path)
    json_path = tmp_path / "run.json"
    main(["run", str(suite_path), "--out", str(tmp_path / "r.md"), "--json", str(json_path)])

    diff_path = tmp_path / "diff.md"
    exit_code = main(["compare", str(json_path), str(json_path), "--out", str(diff_path)])

    assert exit_code == 0
    assert diff_path.exists()
    assert "Regression Diff" in diff_path.read_text()


def test_cli_init_scaffolds_a_runnable_suite(tmp_path):
    target = tmp_path / "new_suite"
    exit_code = main(["init", str(target), "--name", "My Suite"])
    assert exit_code == 0
    for filename in ("suite.yaml", "scorecard.yaml", "cases.yaml", "agent.py"):
        assert (target / filename).exists()

    # The scaffolded suite should be runnable as-is, even though its case
    # is a placeholder that is expected to fail until the user edits it.
    run_exit_code = main(["run", str(target / "suite.yaml"), "--out", str(target / "report.md")])
    assert run_exit_code == 0
    assert (target / "report.md").exists()


def test_cli_init_does_not_overwrite_without_force(tmp_path, capsys):
    target = tmp_path / "suite"
    main(["init", str(target)])
    (target / "suite.yaml").write_text("custom content")

    main(["init", str(target)])
    assert (target / "suite.yaml").read_text() == "custom content"

    main(["init", str(target), "--force"])
    assert (target / "suite.yaml").read_text() != "custom content"


def test_example_support_agent_suite_passes():
    """Smoke test the committed example: it should run clean with 100% pass."""
    repo_root = Path(__file__).resolve().parent.parent
    suite_path = repo_root / "examples" / "support_agent" / "suite.yaml"
    json_path = repo_root / "tests" / "_tmp_example_run.json"

    exit_code = main(
        [
            "run",
            str(suite_path),
            "--out",
            str(json_path.with_suffix(".md")),
            "--json",
            str(json_path),
        ]
    )
    try:
        assert exit_code == 0
        data = json.loads(json_path.read_text())
        assert data["summary"]["failed"] == 0
    finally:
        json_path.unlink(missing_ok=True)
        json_path.with_suffix(".md").unlink(missing_ok=True)
