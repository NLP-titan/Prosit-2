#!/usr/bin/env python3
"""BackendForge Evaluation Suite — main entry point.

Usage:
    # Run all scenarios (backend must be running on localhost:8000)
    python -m evals.run

    # Run specific scenarios
    python -m evals.run s1_todo s2_blog

    # Run with --no-cleanup to keep generated projects for inspection
    python -m evals.run --no-cleanup

    # Output JSON report to a specific path
    python -m evals.run --output results/eval_2025.json
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

from evals.metrics import ScenarioMetrics, compute_aggregate, compute_metrics
from evals.report import generate_json_report, generate_summary
from evals.runner import RunResult, run_scenario
from evals.scenarios import SCENARIOS, get_scenario
from evals.validator import validate


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def run_single(
    scenario_id: str,
    cleanup: bool = True,
) -> tuple[RunResult, ScenarioMetrics]:
    """Run and evaluate a single scenario."""
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario: {scenario_id}")

    logger = logging.getLogger("evals")
    logger.info("=" * 50)
    logger.info("Running: %s (%s) [%s]", scenario.name, scenario.id, scenario.complexity)
    logger.info("=" * 50)

    # Run the conversation
    run_result = await run_scenario(scenario, cleanup=cleanup)

    # Validate if build completed
    validation = None
    if run_result.completed and run_result.api_url:
        logger.info("Validating generated API at %s...", run_result.api_url)
        validation = await validate(scenario, run_result.api_url)
    elif run_result.completed:
        logger.warning("Build completed but no api_url available")

    # Compute metrics
    metrics = compute_metrics(
        run_result,
        validation,
        scenario_name=scenario.name,
        complexity=scenario.complexity,
    )

    return run_result, metrics


async def main(
    scenario_ids: list[str] | None = None,
    cleanup: bool = True,
    output: str | None = None,
    verbose: bool = False,
) -> int:
    """Run evaluation suite."""
    _setup_logging(verbose)
    logger = logging.getLogger("evals")

    # Determine which scenarios to run
    if scenario_ids:
        scenarios = []
        for sid in scenario_ids:
            s = get_scenario(sid)
            if s is None:
                logger.error("Unknown scenario: %s", sid)
                return 1
            scenarios.append(s)
    else:
        scenarios = SCENARIOS

    logger.info("BackendForge Evaluation Suite")
    logger.info("Scenarios to run: %d", len(scenarios))
    logger.info("")

    # Run scenarios sequentially (each uses Docker ports, can't run in parallel)
    all_metrics: list[ScenarioMetrics] = []
    start = time.time()

    for scenario in scenarios:
        try:
            _, metrics = await run_single(scenario.id, cleanup=cleanup)
            all_metrics.append(metrics)

            status = "PASS" if metrics.completed else "FAIL"
            logger.info(
                "[%s] %s — score: %.1f%%, build: %.0fs, tools: %d",
                status, scenario.name, metrics.final_score * 100,
                metrics.build_time, metrics.tool_calls,
            )
        except Exception as e:
            logger.error("Scenario %s crashed: %s", scenario.id, e, exc_info=True)
            all_metrics.append(ScenarioMetrics(
                scenario_id=scenario.id,
                scenario_name=scenario.name,
                complexity=scenario.complexity,
                error=str(e),
            ))

        logger.info("")

    elapsed = time.time() - start

    # Compute aggregate
    aggregate = compute_aggregate(all_metrics)

    # Generate reports
    summary = generate_summary(all_metrics, aggregate)
    print(summary)

    # JSON report
    output_path = Path(output) if output else Path(f"evals/results/eval_{int(time.time())}.json")
    json_path = generate_json_report(all_metrics, aggregate, output_path)
    logger.info("JSON report written to: %s", json_path)
    logger.info("Total evaluation time: %.0fs", elapsed)

    # Return 0 if all passed, 1 if any failed
    return 0 if aggregate.completion_rate == 1.0 else 1


def cli() -> None:
    parser = argparse.ArgumentParser(description="BackendForge Evaluation Suite")
    parser.add_argument(
        "scenarios",
        nargs="*",
        help="Scenario IDs to run (default: all)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep generated projects after evaluation",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(main(
        scenario_ids=args.scenarios or None,
        cleanup=not args.no_cleanup,
        output=args.output,
        verbose=args.verbose,
    ))
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
