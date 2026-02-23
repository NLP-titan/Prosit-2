"""Integration test for PlanningAgent — calls the real LLM.

Requires OPENROUTER_API_KEY in .env. Run from the repo root:
    source venv/bin/activate && python backend/tests/test_planning_integration.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.agents.planning import PlanningAgent
from app.agent.base import AgentEvent
from app.agent.state import (
    EntitySpec,
    FieldSpec,
    Phase,
    ProjectSpec,
    Relationship,
    SharedState,
    Task,
    TaskManifest,
)
from app.models.project import Project


# ── Mock data ────────────────────────────────────────────────────


def make_bookstore_spec() -> ProjectSpec:
    return ProjectSpec(
        entities=[
            EntitySpec(
                name="Book",
                fields=[
                    FieldSpec(name="title", type="str", nullable=False),
                    FieldSpec(name="isbn", type="str", nullable=False, unique=True),
                    FieldSpec(name="price", type="float", nullable=False),
                ],
            ),
            EntitySpec(
                name="Author",
                fields=[
                    FieldSpec(name="name", type="str", nullable=False),
                    FieldSpec(name="bio", type="str", nullable=True),
                ],
            ),
        ],
        relationships=[
            Relationship(entity_a="Book", entity_b="Author", type="many_to_one"),
        ],
        endpoints="crud_default",
        database="postgresql",
    )


def make_bookstore_manifest() -> TaskManifest:
    return TaskManifest(
        tasks=[
            Task(id="t1", type="scaffold", description="Scaffold project", agent="scaffold", dependencies=[]),
            Task(id="t2", type="create_models", description="Create Author model", agent="database", dependencies=["t1"], status="completed"),
            Task(id="t3", type="create_models", description="Create Book model", agent="database", dependencies=["t1"], status="completed"),
            Task(id="t4", type="create_routes", description="Create Author routes", agent="api", dependencies=["t2", "t3"], status="completed"),
            Task(id="t5", type="create_routes", description="Create Book routes", agent="api", dependencies=["t2", "t3"], status="completed"),
            Task(id="t6", type="docker_up", description="Docker up", agent="devops", dependencies=["t4", "t5"], status="completed"),
        ]
    )


# ── Validation helpers ───────────────────────────────────────────

VALID_TASK_TYPES = {"scaffold", "create_models", "create_routes", "docker_up"}
VALID_AGENTS = {"scaffold", "database", "api", "devops"}


def validate_manifest(manifest: TaskManifest, is_delta: bool = False) -> list[str]:
    """Validate a TaskManifest and return a list of issues (empty = valid)."""
    issues = []

    if not manifest.tasks:
        issues.append("Manifest has no tasks")
        return issues

    task_ids = {t.id for t in manifest.tasks}

    for task in manifest.tasks:
        if not task.id:
            issues.append(f"Task missing id: {task}")
        if task.type not in VALID_TASK_TYPES:
            issues.append(f"Task '{task.id}' has invalid type: {task.type}")
        if task.agent not in VALID_AGENTS:
            issues.append(f"Task '{task.id}' has invalid agent: {task.agent}")
        for dep in task.dependencies:
            if dep not in task_ids:
                if is_delta:
                    pass  # Delta tasks may reference existing IDs not in this batch
                else:
                    issues.append(f"Task '{task.id}' depends on unknown task: {dep}")

    if not is_delta:
        scaffold_tasks = [t for t in manifest.tasks if t.type == "scaffold"]
        if not scaffold_tasks:
            issues.append("No scaffold task found")
        elif scaffold_tasks[0].dependencies:
            issues.append("Scaffold task should have no dependencies")

        docker_tasks = [t for t in manifest.tasks if t.type == "docker_up"]
        if not docker_tasks:
            issues.append("No docker_up task found")

    if len(task_ids) != len(manifest.tasks):
        issues.append("Duplicate task IDs detected")

    return issues


# ── Test runners ─────────────────────────────────────────────────


async def test_full_planning():
    """Test: Full planning with bookstore spec -> complete TaskManifest."""
    print("\n--- Test: Full Planning (Bookstore) ---")

    spec = make_bookstore_spec()
    state = SharedState(project_id="test-integration", current_phase=Phase.PLANNING)
    state.spec = spec

    project = Project(id="test-integration", name="bookstore", app_port=9001, db_port=5501)

    agent = PlanningAgent()
    events: list[AgentEvent] = []
    text_parts: list[str] = []

    print("Calling LLM...")
    async for event in agent.run(state=state, project=project):
        events.append(event)
        if event.type == "agent_message_delta":
            token = event.data.get("token", "")
            text_parts.append(token)
            print(token, end="", flush=True)
        elif event.type == "tool_call_start":
            print(f"\n  [tool] {event.data.get('tool')}({json.dumps(event.data.get('arguments', {}))[:100]}...)")
        elif event.type == "tool_call_result":
            result = event.data.get("result", "")
            print(f"  [result] {result[:120]}...")
        elif event.type == "error":
            print(f"\n  [ERROR] {event.data.get('message')}")

    result = await agent.get_result()
    print(f"\n\nAgent result status: {result.status}")

    if result.status != "success":
        print(f"FAIL: Agent returned status={result.status}, error={result.error}")
        return False

    if result.manifest is None:
        print("FAIL: No manifest in result (submit_plan was not called)")
        return False

    manifest = result.manifest
    print(f"Manifest has {len(manifest.tasks)} tasks:")
    for t in manifest.tasks:
        print(f"  {t.id}: [{t.type}] {t.description} (agent={t.agent}, deps={t.dependencies})")

    issues = validate_manifest(manifest, is_delta=False)
    if issues:
        print(f"FAIL: Manifest validation issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    # Check the manifest actually respects dependency ordering
    manifest_copy = TaskManifest.from_dict(manifest.to_dict())
    execution_order = []
    while not manifest_copy.all_complete():
        next_task = manifest_copy.get_next_task()
        if next_task is None:
            print("FAIL: Dependency deadlock during simulated execution")
            return False
        execution_order.append(next_task.id)
        manifest_copy.mark_complete(next_task.id)

    print(f"Execution order: {' -> '.join(execution_order)}")
    print("PASS: Full planning produced valid, executable manifest")
    return True


async def test_delta_planning():
    """Test: Delta planning — add a Category entity to existing bookstore."""
    print("\n--- Test: Delta Planning (Add Category) ---")

    spec = make_bookstore_spec()
    spec.entities.append(
        EntitySpec(
            name="Category",
            fields=[
                FieldSpec(name="name", type="str", nullable=False),
                FieldSpec(name="description", type="str", nullable=True),
            ],
        )
    )
    spec.relationships.append(
        Relationship(entity_a="Book", entity_b="Category", type="many_to_one"),
    )

    state = SharedState(project_id="test-delta", current_phase=Phase.PLANNING)
    state.spec = spec
    state.manifest = make_bookstore_manifest()

    project = Project(id="test-delta", name="bookstore", app_port=9001, db_port=5501)

    agent = PlanningAgent()
    events: list[AgentEvent] = []

    print("Calling LLM for delta plan...")
    async for event in agent.run(
        state=state,
        project=project,
        user_message="Add a Category entity with name and description fields. Books belong to a category.",
    ):
        events.append(event)
        if event.type == "agent_message_delta":
            print(event.data.get("token", ""), end="", flush=True)
        elif event.type == "tool_call_start":
            print(f"\n  [tool] {event.data.get('tool')}({json.dumps(event.data.get('arguments', {}))[:100]}...)")
        elif event.type == "tool_call_result":
            result = event.data.get("result", "")
            print(f"  [result] {result[:120]}...")
        elif event.type == "error":
            print(f"\n  [ERROR] {event.data.get('message')}")

    result = await agent.get_result()
    print(f"\n\nAgent result status: {result.status}")

    if result.status != "success":
        print(f"FAIL: Agent returned status={result.status}, error={result.error}")
        return False

    if result.manifest is None:
        print("FAIL: No manifest in result")
        return False

    manifest = result.manifest
    print(f"Delta manifest has {len(manifest.tasks)} new tasks:")
    for t in manifest.tasks:
        print(f"  {t.id}: [{t.type}] {t.description} (agent={t.agent}, deps={t.dependencies})")

    issues = validate_manifest(manifest, is_delta=True)
    if issues:
        print(f"FAIL: Delta manifest validation issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    existing_ids = {t.id for t in state.manifest.tasks}
    new_ids = {t.id for t in manifest.tasks}
    collisions = existing_ids & new_ids
    if collisions:
        print(f"FAIL: Delta task IDs collide with existing: {collisions}")
        return False

    print("PASS: Delta planning produced valid new tasks with no ID collisions")
    return True


async def main():
    print("=" * 60)
    print("PlanningAgent Integration Tests (LLM)")
    print("=" * 60)

    results = {}

    results["full_planning"] = await test_full_planning()
    results["delta_planning"] = await test_delta_planning()

    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    print(f"Results: {passed} passed, {failed} failed")
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")

    if failed:
        sys.exit(1)
    print("\nAll integration tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
