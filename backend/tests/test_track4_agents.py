"""Integration test for Track 4 Implementation Agents.

Runs ScaffoldAgent → DatabaseAgent → APIAgent sequentially using the
mock bookstore data from the Phase 2 spec (Section 7).

Usage:
  # From inside the backend Docker container:
  python -m tests.test_track4_agents

  # Or via docker exec:
  docker exec kruya-jenjen-backend-1 python -m tests.test_track4_agents
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.state import SharedState, Task
from app.agent.agents.scaffold import ScaffoldAgent, AgentEvent
from app.agent.agents.database import DatabaseAgent
from app.agent.agents.api import APIAgent
from app.models.project import Project, ProjectState
from app.config import settings


# ---------------------------------------------------------------------------
# Mock data from spec Section 7
# ---------------------------------------------------------------------------

MOCK_AUTHOR_ENTITY = {
    "name": "Author",
    "fields": [
        {"name": "name", "type": "str", "nullable": False},
        {"name": "bio", "type": "str", "nullable": True},
    ],
}

MOCK_BOOK_ENTITY = {
    "name": "Book",
    "fields": [
        {"name": "title", "type": "str", "nullable": False},
        {"name": "isbn", "type": "str", "nullable": False, "unique": True},
        {"name": "price", "type": "float", "nullable": False},
    ],
}

MOCK_RELATIONSHIPS = [
    {"entity_a": "Book", "entity_b": "Author", "type": "many_to_one"},
]

MOCK_TASKS = [
    Task(id="t1", type="scaffold", description="Scaffold project", agent="scaffold", dependencies=[]),
    Task(
        id="t2",
        type="create_models",
        description="Create Author model",
        agent="database",
        dependencies=["t1"],
        context={
            "entity": MOCK_AUTHOR_ENTITY,
            "relationships": [r for r in MOCK_RELATIONSHIPS if "Author" in (r["entity_a"], r["entity_b"])],
        },
    ),
    Task(
        id="t3",
        type="create_models",
        description="Create Book model",
        agent="database",
        dependencies=["t1"],
        context={
            "entity": MOCK_BOOK_ENTITY,
            "relationships": MOCK_RELATIONSHIPS,
        },
    ),
    Task(
        id="t4",
        type="create_routes",
        description="Create Author CRUD routes",
        agent="api",
        dependencies=["t2", "t3"],
        context={
            "entity": MOCK_AUTHOR_ENTITY,
            "relationships": [r for r in MOCK_RELATIONSHIPS if "Author" in (r["entity_a"], r["entity_b"])],
        },
    ),
    Task(
        id="t5",
        type="create_routes",
        description="Create Book CRUD routes",
        agent="api",
        dependencies=["t2", "t3"],
        context={
            "entity": MOCK_BOOK_ENTITY,
            "relationships": MOCK_RELATIONSHIPS,
        },
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_agent_for_task(task: Task, project: Project):
    """Return the right agent class for a task type."""
    agents = {
        "scaffold": ScaffoldAgent,
        "database": DatabaseAgent,
        "api": APIAgent,
    }
    cls = agents.get(task.agent)
    if cls is None:
        raise ValueError(f"Unknown agent: {task.agent}")
    return cls(project)


async def run_agent(agent, state: SharedState, task: Task) -> dict | None:
    """Run an agent, collect events, return the AgentResult data."""
    result_data = None
    event_count = 0
    tool_calls = []

    async for event in agent.run(state, task):
        event_count += 1

        if event.type == "agent_message_delta":
            # Print LLM text as it streams
            print(event.data.get("token", ""), end="", flush=True)
        elif event.type == "agent_message_end":
            print()  # newline after streamed text
        elif event.type == "tool_call_start":
            tool_name = event.data.get("tool", "?")
            tool_calls.append(tool_name)
            print(f"  -> tool: {tool_name}")
        elif event.type == "tool_call_result":
            result_preview = event.data.get("result", "")[:200]
            print(f"     result: {result_preview}")
        elif event.type == "agent_result":
            result_data = event.data
        elif event.type == "error":
            print(f"  !! ERROR: {event.data.get('message', '')}")

    return result_data


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("Track 4 Implementation Agents — Integration Test")
    print("Using mock bookstore data (Author + Book)")
    print("=" * 60)

    # Create a test project
    project = Project(
        id="test-track4",
        name="bookstore",
        description="A bookstore API with books and authors",
        app_port=9099,
        db_port=5599,
    )

    # Clean up any previous test
    import shutil
    if project.directory.exists():
        shutil.rmtree(project.directory)
    project.directory.mkdir(parents=True, exist_ok=True)

    state = SharedState(project_id=project.id)

    results = {}

    for task in MOCK_TASKS:
        print()
        print("-" * 60)
        print(f"Task {task.id}: {task.type} (agent={task.agent})")
        print("-" * 60)

        # Check dependencies
        deps_met = True
        for dep in task.dependencies:
            dep_result = results.get(dep)
            if dep_result is None or dep_result.get("status") != "success":
                print(f"  SKIPPED — dependency {dep} not completed successfully")
                results[task.id] = {"status": "skipped"}
                deps_met = False
                break
        if not deps_met:
            continue

        agent = get_agent_for_task(task, project)
        result = await run_agent(agent, state, task)
        results[task.id] = result or {"status": "no_result"}

        if result:
            print(f"\n  Result: status={result.get('status')}")
            print(f"  Message: {result.get('message', 'n/a')}")
            print(f"  Files: {result.get('files_modified', [])}")
            if result.get("error"):
                print(f"  Error: {result['error']}")

    # Summary
    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for task in MOCK_TASKS:
        r = results.get(task.id, {})
        status = r.get("status", "unknown")
        icon = "OK" if status == "success" else "FAIL" if status == "error" else "SKIP"
        print(f"  [{icon}] {task.id}: {task.type} ({task.agent})")

    # Check generated files
    print()
    print("Generated files:")
    if project.directory.exists():
        for p in sorted(project.directory.rglob("*")):
            if p.is_file() and "__pycache__" not in str(p) and ".git" not in str(p):
                rel = p.relative_to(project.directory)
                print(f"  {rel}")
    else:
        print("  (no project directory)")


if __name__ == "__main__":
    asyncio.run(main())
