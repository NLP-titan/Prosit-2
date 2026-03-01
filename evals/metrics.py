"""Metric computation and weighted scoring."""

from __future__ import annotations

from dataclasses import dataclass, field

from evals.config import (
    IDEAL_BUILD_TIME,
    IDEAL_LLM_ROUNDS,
    MAX_BUILD_TIME,
    MAX_LLM_ROUNDS,
    WEIGHT_BUILD_TIME,
    WEIGHT_COMPLETION,
    WEIGHT_ENDPOINTS,
    WEIGHT_LLM_ROUNDS,
    WEIGHT_SCHEMA,
)
from evals.runner import RunResult
from evals.validator import ValidationResult


@dataclass
class ScenarioMetrics:
    """Computed metrics for a single scenario run."""

    scenario_id: str
    scenario_name: str
    complexity: str

    # Raw values
    completed: bool = False
    build_time: float = 0.0
    tool_calls: int = 0
    agent_messages: int = 0
    ask_user_count: int = 0
    error: str | None = None

    # Validation scores (0.0–1.0)
    endpoint_coverage: float = 0.0
    schema_match_score: float = 0.0

    # Component scores (0.0–1.0)
    completion_score: float = 0.0
    build_time_score: float = 0.0
    llm_rounds_score: float = 0.0

    # Weighted final score (0.0–1.0)
    final_score: float = 0.0

    # Detail breakdown
    schema_details: list[dict] = field(default_factory=list)
    endpoint_details: list[dict] = field(default_factory=list)


def _linear_score(value: float, ideal: float, worst: float) -> float:
    """Linear interpolation: ideal → 1.0, worst → 0.0, clamped."""
    if ideal == worst:
        return 1.0
    score = (worst - value) / (worst - ideal)
    return max(0.0, min(1.0, score))


def compute_metrics(
    run: RunResult,
    validation: ValidationResult | None,
    scenario_name: str = "",
    complexity: str = "",
) -> ScenarioMetrics:
    """Compute all metrics for a single scenario run."""
    m = ScenarioMetrics(
        scenario_id=run.scenario_id,
        scenario_name=scenario_name,
        complexity=complexity,
        completed=run.completed,
        build_time=run.build_time,
        tool_calls=run.tool_calls,
        agent_messages=run.agent_messages,
        ask_user_count=run.ask_user_count,
        error=run.error,
    )

    # ── Completion score ───────────────────────────────────────
    m.completion_score = 1.0 if run.completed else 0.0

    # ── Build time score ───────────────────────────────────────
    if run.completed:
        m.build_time_score = _linear_score(run.build_time, IDEAL_BUILD_TIME, MAX_BUILD_TIME)
    else:
        m.build_time_score = 0.0

    # ── LLM rounds score (tool_calls as proxy) ─────────────────
    m.llm_rounds_score = _linear_score(run.tool_calls, IDEAL_LLM_ROUNDS, MAX_LLM_ROUNDS)

    # ── Validation scores ──────────────────────────────────────
    if validation:
        m.endpoint_coverage = validation.endpoint_coverage
        m.schema_match_score = validation.schema_match_score

        m.schema_details = [
            {
                "entity": sr.entity_name,
                "expected": sr.fields_expected,
                "found": sr.fields_found,
                "missing": sr.missing_fields,
                "score": sr.score,
            }
            for sr in validation.schema_results
        ]
        m.endpoint_details = [
            {
                "method": er.method,
                "path": er.path,
                "status": er.status_code,
                "success": er.success,
                "error": er.error,
            }
            for er in validation.endpoint_results
        ]

    # ── Weighted final score ───────────────────────────────────
    m.final_score = (
        WEIGHT_COMPLETION * m.completion_score
        + WEIGHT_SCHEMA * m.schema_match_score
        + WEIGHT_ENDPOINTS * m.endpoint_coverage
        + WEIGHT_BUILD_TIME * m.build_time_score
        + WEIGHT_LLM_ROUNDS * m.llm_rounds_score
    )

    return m


@dataclass
class AggregateMetrics:
    """Summary across all scenario runs."""

    total_scenarios: int = 0
    completed_count: int = 0
    completion_rate: float = 0.0

    avg_build_time: float = 0.0
    avg_tool_calls: float = 0.0
    avg_endpoint_coverage: float = 0.0
    avg_schema_match: float = 0.0
    avg_final_score: float = 0.0

    by_complexity: dict[str, dict] = field(default_factory=dict)


def compute_aggregate(metrics_list: list[ScenarioMetrics]) -> AggregateMetrics:
    """Compute aggregate stats across all scenario runs."""
    agg = AggregateMetrics(total_scenarios=len(metrics_list))
    if not metrics_list:
        return agg

    agg.completed_count = sum(1 for m in metrics_list if m.completed)
    agg.completion_rate = agg.completed_count / agg.total_scenarios

    completed = [m for m in metrics_list if m.completed]
    if completed:
        agg.avg_build_time = sum(m.build_time for m in completed) / len(completed)

    agg.avg_tool_calls = sum(m.tool_calls for m in metrics_list) / agg.total_scenarios
    agg.avg_endpoint_coverage = sum(m.endpoint_coverage for m in metrics_list) / agg.total_scenarios
    agg.avg_schema_match = sum(m.schema_match_score for m in metrics_list) / agg.total_scenarios
    agg.avg_final_score = sum(m.final_score for m in metrics_list) / agg.total_scenarios

    # Group by complexity
    by_cx: dict[str, list[ScenarioMetrics]] = {}
    for m in metrics_list:
        by_cx.setdefault(m.complexity, []).append(m)

    for cx, items in by_cx.items():
        cx_completed = [m for m in items if m.completed]
        agg.by_complexity[cx] = {
            "count": len(items),
            "completed": len(cx_completed),
            "avg_score": sum(m.final_score for m in items) / len(items),
            "avg_build_time": sum(m.build_time for m in cx_completed) / len(cx_completed) if cx_completed else 0,
        }

    return agg
