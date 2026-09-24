"""The `agent-evals` command line interface.

Three commands:

- `agent-evals run <suite.yaml>` runs a suite and writes a Markdown report
  and, optionally, a JSON run file for later comparison.
- `agent-evals compare <old.json> <new.json>` renders a regression diff
  between two JSON run files.
- `agent-evals init [path]` scaffolds a new suite: a suite file, a
  scorecard, a cases file, and a stub agent, ready to edit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_evals.judge.fake_judge import FakeJudge
from agent_evals.report import from_json, render_diff, render_markdown, to_json
from agent_evals.runner import Runner
from agent_evals.suite import load_suite


def _build_judge(kind: str, model: str | None):
    if kind == "fake":
        return FakeJudge()
    if kind == "anthropic":
        from agent_evals.judge.anthropic_judge import AnthropicJudge

        return AnthropicJudge(model=model) if model else AnthropicJudge()
    if kind == "none":
        return None
    raise ValueError(f"unknown judge kind '{kind}': expected 'fake', 'anthropic', or 'none'")


def cmd_run(args: argparse.Namespace) -> int:
    suite = load_suite(args.suite)
    judge_kind = args.judge or suite.judge_kind
    judge_model = args.judge_model or suite.judge_model
    judge = _build_judge(judge_kind, judge_model)

    agent = suite.load_agent()
    runner = Runner(agent=agent, scorecard=suite.scorecard, judge=judge)
    results = runner.run_suite(suite.cases)

    markdown = render_markdown(results, suite.scorecard, suite_name=suite.name)
    out_path = Path(args.out)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"wrote report to {out_path}")

    if args.json:
        json_path = Path(args.json)
        json_path.write_text(
            json.dumps(to_json(results, suite.scorecard, suite_name=suite.name), indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote run data to {json_path}")

    passed = sum(1 for r in results if r.passed)
    print(f"{passed}/{len(results)} cases passed")

    if args.fail_under is not None:
        pass_rate = passed / len(results) if results else 0.0
        if pass_rate < args.fail_under:
            print(f"pass rate {pass_rate:.2%} is below --fail-under {args.fail_under:.2%}")
            return 1

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    old_data = json.loads(Path(args.old).read_text(encoding="utf-8"))
    new_data = json.loads(Path(args.new).read_text(encoding="utf-8"))
    old_results = from_json(old_data)
    new_results = from_json(new_data)

    diff = render_diff(old_results, new_results)
    if args.out:
        Path(args.out).write_text(diff, encoding="utf-8")
        print(f"wrote diff to {args.out}")
    else:
        print(diff)
    return 0


SUITE_TEMPLATE = """name: {title}
agent: agent.py:run_agent
scorecard: scorecard.yaml
cases: cases.yaml
judge: fake
"""

SCORECARD_TEMPLATE = """name: {title} Scorecard
pass_threshold: 0.75

dimensions:
  - name: task_success
    scorer: task_success
    weight: 0.4
    threshold: 0.8
    config:
      mode: contains

  - name: tool_correctness
    scorer: tool_correctness
    weight: 0.3
    threshold: 0.8

  - name: quality
    scorer: llm_judge
    weight: 0.2
    threshold: 0.6
    config:
      rubric: >
        Rate how helpful and on-tone this response is, from 0.0 to 1.0.

  - name: cost
    scorer: cost
    weight: 0.1
    threshold: 0.8
    config:
      max_cost_usd: 0.01
"""

CASES_TEMPLATE = """- id: example-case-1
  input: "Replace this with a real input to your agent."
  tags: [smoke]
  expected_output_contains:
    - "replace with a phrase you expect in the output"
  expected_tool_calls: []
"""

AGENT_TEMPLATE = '''"""A stub agent for a new eval suite. Replace run_agent with a call into the
agent you actually want to evaluate."""

from agent_evals import AgentResponse, ToolCall


def run_agent(message: str) -> AgentResponse:
    return AgentResponse(output=f"You said: {message}", tool_calls=[], model=None, cost_usd=0.0)
'''


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path)
    target.mkdir(parents=True, exist_ok=True)
    title = args.name or target.name or "New Eval Suite"

    files = {
        "suite.yaml": SUITE_TEMPLATE.format(title=title),
        "scorecard.yaml": SCORECARD_TEMPLATE.format(title=title),
        "cases.yaml": CASES_TEMPLATE,
        "agent.py": AGENT_TEMPLATE,
    }
    for filename, content in files.items():
        file_path = target / filename
        if file_path.exists() and not args.force:
            print(f"skipping {file_path}, already exists (use --force to overwrite)")
            continue
        file_path.write_text(content, encoding="utf-8")
        print(f"wrote {file_path}")

    print(
        f"\nscaffolded a suite in {target}. Run it with:\n  agent-evals run {target / 'suite.yaml'}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-evals", description="Evaluate LLM agents against a scorecard."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an eval suite and write a report.")
    run_parser.add_argument("suite", help="Path to a suite YAML file.")
    run_parser.add_argument(
        "--out", default="report.md", help="Markdown report output path (default: report.md)."
    )
    run_parser.add_argument("--json", default=None, help="Also write a JSON run file to this path.")
    run_parser.add_argument(
        "--judge",
        choices=["fake", "anthropic", "none"],
        default=None,
        help="Override the suite's judge (default: use the suite's own 'judge' field, or fake).",
    )
    run_parser.add_argument("--judge-model", default=None, help="Override the judge model id.")
    run_parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Exit with status 1 if the pass rate falls below this fraction (e.g. 0.8).",
    )
    run_parser.set_defaults(func=cmd_run)

    compare_parser = subparsers.add_parser("compare", help="Diff two JSON run files.")
    compare_parser.add_argument("old", help="Path to the older run.json.")
    compare_parser.add_argument("new", help="Path to the newer run.json.")
    compare_parser.add_argument(
        "--out", default=None, help="Write the diff to this path instead of stdout."
    )
    compare_parser.set_defaults(func=cmd_compare)

    init_parser = subparsers.add_parser("init", help="Scaffold a new eval suite.")
    init_parser.add_argument(
        "path", nargs="?", default=".", help="Directory to scaffold into (default: .)."
    )
    init_parser.add_argument(
        "--name", default=None, help="Suite name (default: the directory name)."
    )
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    init_parser.set_defaults(func=cmd_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
