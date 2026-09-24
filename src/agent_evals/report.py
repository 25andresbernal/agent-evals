"""Report: renders eval results as Markdown or JSON, and diffs two runs.

The JSON format is the interchange format: `agent-evals run` writes it with
`--json`, and `agent-evals compare` reads two of them to produce a
regression diff. It is also what a CI job would parse to fail a build on a
score drop.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from agent_evals.runner import CaseResult, ToolCall
from agent_evals.scorecard import Scorecard
from agent_evals.scorers.base import ScoreResult


@dataclass
class RunSummary:
    total: int
    passed: int
    failed: int
    pass_rate: float
    avg_weighted_score: float


def summarize(results: list[CaseResult]) -> RunSummary:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.weighted_score for r in results) / total if total else 0.0
    return RunSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=passed / total if total else 0.0,
        avg_weighted_score=avg_score,
    )


def to_json(
    results: list[CaseResult], scorecard: Scorecard, suite_name: str = "Eval Suite"
) -> dict[str, Any]:
    summary = summarize(results)
    return {
        "suite": suite_name,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scorecard": {
            "name": scorecard.name,
            "pass_threshold": scorecard.pass_threshold,
            "dimensions": [
                {"name": d.name, "weight": d.weight, "threshold": d.threshold}
                for d in scorecard.dimensions
            ],
        },
        "summary": {
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "pass_rate": round(summary.pass_rate, 4),
            "avg_weighted_score": round(summary.avg_weighted_score, 4),
        },
        "cases": [
            {
                "id": r.case_id,
                "tags": r.tags,
                "input": r.input,
                "output": r.output,
                "tool_calls": [{"name": c.name, "args": c.args} for c in r.tool_calls],
                "latency_ms": round(r.latency_ms, 4),
                "cost_usd": round(r.cost_usd, 6),
                "weighted_score": round(r.weighted_score, 4),
                "passed": r.passed,
                "dimensions": {
                    name: {"score": round(sr.score, 4), "passed": sr.passed, "detail": sr.detail}
                    for name, sr in r.dimension_scores.items()
                },
            }
            for r in results
        ],
    }


def from_json(data: dict[str, Any]) -> list[CaseResult]:
    results = []
    for case in data["cases"]:
        dimension_scores = {
            name: ScoreResult(score=d["score"], passed=d["passed"], detail=d.get("detail", ""))
            for name, d in case["dimensions"].items()
        }
        results.append(
            CaseResult(
                case_id=case["id"],
                input=case.get("input", ""),
                output=case.get("output", ""),
                tags=case.get("tags", []),
                tool_calls=[
                    ToolCall(name=c["name"], args=c.get("args", {}))
                    for c in case.get("tool_calls", [])
                ],
                latency_ms=case.get("latency_ms", 0.0),
                cost_usd=case.get("cost_usd", 0.0),
                dimension_scores=dimension_scores,
                weighted_score=case["weighted_score"],
                passed=case["passed"],
            )
        )
    return results


def render_markdown(
    results: list[CaseResult], scorecard: Scorecard, suite_name: str = "Eval Suite"
) -> str:
    summary = summarize(results)
    lines: list[str] = []
    lines.append(f"# {suite_name}")
    lines.append("")
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(
        f"Generated {generated}. {summary.total} cases, {summary.passed} passed, "
        f"{summary.failed} failed ({summary.pass_rate:.0%} pass rate). "
        f"Average weighted score {summary.avg_weighted_score:.2f} "
        f"against a pass threshold of {scorecard.pass_threshold:.2f}."
    )
    lines.append("")

    lines.append("## Summary by dimension")
    lines.append("")
    lines.append("| Dimension | Weight | Avg score | Threshold | Cases below threshold |")
    lines.append("|---|---|---|---|---|")
    for dim in scorecard.dimensions:
        scores = [
            r.dimension_scores[dim.name].score for r in results if dim.name in r.dimension_scores
        ]
        avg = sum(scores) / len(scores) if scores else 0.0
        below = sum(1 for s in scores if s < dim.threshold)
        lines.append(f"| {dim.name} | {dim.weight:g} | {avg:.2f} | {dim.threshold:.2f} | {below} |")
    lines.append("")

    lines.append("## Case results")
    lines.append("")
    dim_names = [d.name for d in scorecard.dimensions]
    header = ["Case", "Tags", "Result", "Weighted score", *dim_names]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for r in results:
        tags = ", ".join(r.tags) if r.tags else ""
        result_label = "PASS" if r.passed else "FAIL"
        row = [
            r.case_id,
            tags,
            result_label,
            f"{r.weighted_score:.2f}",
            *(
                f"{r.dimension_scores[name].score:.2f}" if name in r.dimension_scores else "-"
                for name in dim_names
            ),
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    failed_results = [r for r in results if not r.passed]
    if failed_results:
        lines.append("## Failed case details")
        lines.append("")
        for r in failed_results:
            lines.append(f"### {r.case_id}")
            lines.append("")
            lines.append(f"Input: {r.input}")
            lines.append("")
            lines.append(f"Output: {r.output}")
            lines.append("")
            for name, sr in r.dimension_scores.items():
                mark = "ok" if sr.score >= _threshold_for(scorecard, name) else "below threshold"
                lines.append(f"- {name}: {sr.score:.2f} ({mark}) - {sr.detail}")
            lines.append("")

    return "\n".join(lines)


def _threshold_for(scorecard: Scorecard, dimension_name: str) -> float:
    for d in scorecard.dimensions:
        if d.name == dimension_name:
            return d.threshold
    return 0.0


def render_diff(old_results: list[CaseResult], new_results: list[CaseResult]) -> str:
    """Render a Markdown regression diff between two runs of the same suite."""
    old_by_id = {r.case_id: r for r in old_results}
    new_by_id = {r.case_id: r for r in new_results}
    all_ids = sorted(set(old_by_id) | set(new_by_id))

    old_summary = summarize(old_results)
    new_summary = summarize(new_results)

    lines: list[str] = []
    lines.append("# Regression Diff")
    lines.append("")
    old_avg = old_summary.avg_weighted_score
    new_avg = new_summary.avg_weighted_score
    lines.append(
        f"Pass rate: {old_summary.pass_rate:.0%} -> {new_summary.pass_rate:.0%}. "
        f"Average weighted score: {old_avg:.2f} -> {new_avg:.2f}."
    )
    lines.append("")

    lines.append("| Case | Old | New | Score delta | Change |")
    lines.append("|---|---|---|---|---|")
    changed_only: list[str] = []
    for case_id in all_ids:
        old = old_by_id.get(case_id)
        new = new_by_id.get(case_id)
        if old is None:
            lines.append(
                f"| {case_id} | (new case) | {'PASS' if new.passed else 'FAIL'} | - | added |"
            )
            continue
        if new is None:
            lines.append(
                f"| {case_id} | {'PASS' if old.passed else 'FAIL'} | (removed) | - | removed |"
            )
            continue

        old_label = "PASS" if old.passed else "FAIL"
        new_label = "PASS" if new.passed else "FAIL"
        delta = new.weighted_score - old.weighted_score
        if old.passed and not new.passed:
            change = "REGRESSION"
        elif not old.passed and new.passed:
            change = "fixed"
        elif abs(delta) >= 0.01:
            change = "changed"
        else:
            change = "unchanged"
        lines.append(f"| {case_id} | {old_label} | {new_label} | {delta:+.2f} | {change} |")
        if change != "unchanged":
            changed_only.append(case_id)

    lines.append("")
    regressions = [
        case_id
        for case_id in all_ids
        if case_id in old_by_id
        and case_id in new_by_id
        and old_by_id[case_id].passed
        and not new_by_id[case_id].passed
    ]
    if regressions:
        lines.append(f"**{len(regressions)} case(s) regressed:** {', '.join(regressions)}")
    else:
        lines.append("No cases regressed from pass to fail.")

    return "\n".join(lines)
