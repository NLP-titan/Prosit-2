"""Generate JSON results and human-readable summary."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from evals.metrics import AggregateMetrics, ScenarioMetrics


def _grade(score: float) -> str:
    if score >= 0.9:
        return "A"
    if score >= 0.8:
        return "B"
    if score >= 0.7:
        return "C"
    if score >= 0.6:
        return "D"
    return "F"


def generate_json_report(
    metrics_list: list[ScenarioMetrics],
    aggregate: AggregateMetrics,
    output_path: Path,
) -> Path:
    """Write full results to a JSON file."""
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "aggregate": asdict(aggregate),
        "scenarios": [asdict(m) for m in metrics_list],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str))
    return output_path


def generate_summary(
    metrics_list: list[ScenarioMetrics],
    aggregate: AggregateMetrics,
) -> str:
    """Generate a human-readable summary string."""
    lines = []
    lines.append("=" * 60)
    lines.append("  BackendForge Evaluation Report")
    lines.append("=" * 60)
    lines.append("")

    # Overall
    grade = _grade(aggregate.avg_final_score)
    lines.append(f"  Overall Score: {aggregate.avg_final_score:.1%}  (Grade: {grade})")
    lines.append(f"  Completion Rate: {aggregate.completion_rate:.0%} ({aggregate.completed_count}/{aggregate.total_scenarios})")
    if aggregate.avg_build_time:
        lines.append(f"  Avg Build Time: {aggregate.avg_build_time:.0f}s")
    lines.append(f"  Avg Tool Calls: {aggregate.avg_tool_calls:.0f}")
    lines.append(f"  Avg Schema Match: {aggregate.avg_schema_match:.1%}")
    lines.append(f"  Avg Endpoint Coverage: {aggregate.avg_endpoint_coverage:.1%}")
    lines.append("")

    # By complexity
    if aggregate.by_complexity:
        lines.append("  By Complexity:")
        for cx in ["trivial", "simple", "medium", "complex"]:
            if cx in aggregate.by_complexity:
                data = aggregate.by_complexity[cx]
                lines.append(
                    f"    {cx:8s}: {data['completed']}/{data['count']} completed, "
                    f"avg score {data['avg_score']:.1%}, "
                    f"avg build {data['avg_build_time']:.0f}s"
                )
        lines.append("")

    # Per scenario
    lines.append("-" * 60)
    lines.append("  Scenario Details")
    lines.append("-" * 60)

    for m in metrics_list:
        status = "PASS" if m.completed else "FAIL"
        lines.append("")
        lines.append(f"  [{status}] {m.scenario_name} ({m.complexity})")
        lines.append(f"    Score: {m.final_score:.1%}  |  Build: {m.build_time:.0f}s  |  Tools: {m.tool_calls}")
        lines.append(f"    Schema: {m.schema_match_score:.0%}  |  Endpoints: {m.endpoint_coverage:.0%}")

        if m.error:
            lines.append(f"    Error: {m.error[:100]}")

        # Schema details
        for sd in m.schema_details:
            if sd["missing"]:
                lines.append(f"    {sd['entity']}: missing [{', '.join(sd['missing'])}]")

        # Failed endpoints
        failed = [e for e in m.endpoint_details if not e["success"]]
        if failed:
            lines.append(f"    Failed endpoints:")
            for e in failed[:5]:
                lines.append(f"      {e['method']} {e['path']} -> {e.get('status') or e.get('error', '?')}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
