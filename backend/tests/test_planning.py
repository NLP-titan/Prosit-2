"""Tests for Track 3: PlanningAgent, planning prompt, and template registry.

These tests validate agent setup, message construction, and registry logic
without requiring an LLM call. They use the mock BookStore ProjectSpec from
the spec document.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


# ── Mock data (from spec doc Section 7) ─────────────────────────


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
    """The expected manifest for the bookstore spec (from spec doc Section 7)."""
    return TaskManifest(
        tasks=[
            Task(id="t1", type="scaffold", description="Scaffold project", agent="scaffold", dependencies=[]),
            Task(id="t2", type="create_models", description="Create Author model", agent="database", dependencies=["t1"]),
            Task(id="t3", type="create_models", description="Create Book model", agent="database", dependencies=["t1"]),
            Task(id="t4", type="create_routes", description="Create Author routes", agent="api", dependencies=["t2", "t3"]),
            Task(id="t5", type="create_routes", description="Create Book routes", agent="api", dependencies=["t2", "t3"]),
            Task(id="t6", type="docker_up", description="Docker up", agent="devops", dependencies=["t4", "t5"]),
        ]
    )


# ── 1. PlanningAgent class setup ────────────────────────────────


def test_agent_class_attributes():
    from app.agent.agents.planning import PlanningAgent

    agent = PlanningAgent()
    assert agent.name == "planning"
    assert "submit_plan" in agent.tool_names
    assert "read_file" in agent.tool_names
    assert "list_directory" in agent.tool_names
    assert agent.max_tool_rounds == 10
    assert len(agent.system_prompt) > 100, "System prompt should be substantial"
    print("  PASS: agent class attributes")


def test_agent_tool_schema_filtering():
    from app.agent.agents.planning import PlanningAgent

    agent = PlanningAgent()
    schemas = agent.get_tool_schemas()
    tool_names = {s["function"]["name"] for s in schemas}
    assert tool_names == {"read_file", "list_directory", "submit_plan"}, (
        f"Expected exactly 3 tools, got: {tool_names}"
    )
    print("  PASS: tool schema filtering")


# ── 2. Message construction ─────────────────────────────────────


def test_full_planning_message_construction():
    """Verify messages built for full planning contain spec and instructions."""
    spec = make_bookstore_spec()
    state = SharedState(project_id="test-project", current_phase=Phase.PLANNING)
    state.spec = spec

    spec_json = json.dumps(state.spec.to_dict(), indent=2)

    # Simulate what PlanningAgent.run() builds
    messages = [{"role": "system", "content": "...system prompt..."}]
    content = f"## Project Spec\n```json\n{spec_json}\n```\n\nProduce a complete TaskManifest for this project."
    messages.append({"role": "user", "content": content})

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Book" in messages[1]["content"]
    assert "Author" in messages[1]["content"]
    assert "many_to_one" in messages[1]["content"]
    assert "complete TaskManifest" in messages[1]["content"]
    print("  PASS: full planning message construction")


def test_delta_planning_message_construction():
    """Verify messages built for delta planning contain existing manifest + change."""
    spec = make_bookstore_spec()
    manifest = make_bookstore_manifest()
    state = SharedState(project_id="test-project", current_phase=Phase.PLANNING)
    state.spec = spec
    state.manifest = manifest

    user_message = "Add a Categories entity with name and description fields"
    spec_json = json.dumps(state.spec.to_dict(), indent=2)
    existing_manifest = json.dumps(state.manifest.to_dict(), indent=2)

    content = (
        f"## Existing TaskManifest\n"
        f"```json\n{existing_manifest}\n```\n\n"
        f"## Project Spec\n"
        f"```json\n{spec_json}\n```\n\n"
        f"## New Requirement\n"
        f"{user_message}\n\n"
        f"Produce ONLY the new tasks to append to the existing manifest. "
        f"Do NOT repeat existing tasks. Continue task IDs from where the "
        f"existing manifest left off."
    )

    assert "Existing TaskManifest" in content
    assert "t1" in content  # existing task IDs present
    assert "t6" in content
    assert "Categories" in content
    assert "ONLY the new tasks" in content
    print("  PASS: delta planning message construction")


# ── 3. Spec serialization round-trip ────────────────────────────


def test_spec_round_trip():
    spec = make_bookstore_spec()
    spec_dict = spec.to_dict()
    spec_json = json.dumps(spec_dict)
    spec_back = ProjectSpec.from_dict(json.loads(spec_json))

    assert len(spec_back.entities) == 2
    assert spec_back.entities[0].name == "Book"
    assert spec_back.entities[1].name == "Author"
    assert len(spec_back.entities[0].fields) == 3
    assert spec_back.relationships[0].type == "many_to_one"
    assert spec_back.database == "postgresql"
    print("  PASS: spec serialization round-trip")


def test_manifest_round_trip():
    manifest = make_bookstore_manifest()
    manifest_dict = manifest.to_dict()
    manifest_json = json.dumps(manifest_dict)
    manifest_back = TaskManifest.from_dict(json.loads(manifest_json))

    assert len(manifest_back.tasks) == 6
    assert manifest_back.tasks[0].type == "scaffold"
    assert manifest_back.tasks[-1].type == "docker_up"
    assert manifest_back.tasks[-1].dependencies == ["t4", "t5"]
    print("  PASS: manifest serialization round-trip")


# ── 4. TaskManifest dependency ordering ─────────────────────────


def test_manifest_dependency_ordering():
    manifest = make_bookstore_manifest()

    first = manifest.get_next_task()
    assert first is not None
    assert first.id == "t1", "Scaffold should be the first runnable task"

    manifest.mark_complete("t1")
    next_task = manifest.get_next_task()
    assert next_task is not None
    assert next_task.id in ("t2", "t3"), "Model tasks should be next after scaffold"

    manifest.mark_complete("t2")
    manifest.mark_complete("t3")
    next_task = manifest.get_next_task()
    assert next_task is not None
    assert next_task.id in ("t4", "t5"), "Route tasks should follow models"

    manifest.mark_complete("t4")
    manifest.mark_complete("t5")
    next_task = manifest.get_next_task()
    assert next_task is not None
    assert next_task.id == "t6", "Docker up should be last"

    manifest.mark_complete("t6")
    assert manifest.all_complete()
    print("  PASS: manifest dependency ordering")


def test_manifest_append_tasks():
    manifest = make_bookstore_manifest()
    assert len(manifest.tasks) == 6

    new_tasks = [
        Task(id="t7", type="create_models", description="Create Category model", agent="database", dependencies=["t1"]),
        Task(id="t8", type="create_routes", description="Create Category routes", agent="api", dependencies=["t2", "t3", "t7"]),
        Task(id="t9", type="docker_up", description="Docker up (delta)", agent="devops", dependencies=["t8"]),
    ]
    manifest.append_tasks(new_tasks)
    assert len(manifest.tasks) == 9
    assert manifest.tasks[-1].id == "t9"
    print("  PASS: manifest append tasks (delta)")


# ── 5. Template registry ────────────────────────────────────────


def test_template_registry_lookup():
    from app.generator.scaffold import (
        TEMPLATE_REGISTRY,
        ADDON_REGISTRY,
        get_template_dir,
        get_available_templates,
        get_compatible_addons,
    )

    assert "fastapi-postgres" in TEMPLATE_REGISTRY
    fp_template = TEMPLATE_REGISTRY["fastapi-postgres"]
    assert fp_template.name == "fastapi-postgres"
    assert fp_template.path.name == "fastapi-postgres"

    template_dir = get_template_dir("fastapi-postgres")
    assert template_dir == fp_template.path
    print("  PASS: template registry lookup")


def test_template_registry_unknown_raises():
    from app.generator.scaffold import get_template_dir

    try:
        get_template_dir("does-not-exist")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "does-not-exist" in str(e)
        assert "fastapi-postgres" in str(e)
    print("  PASS: unknown template raises ValueError")


def test_addon_registry():
    from app.generator.scaffold import ADDON_REGISTRY, get_compatible_addons

    assert "auth" in ADDON_REGISTRY
    assert "relations" in ADDON_REGISTRY
    assert "redis" in ADDON_REGISTRY

    auth = ADDON_REGISTRY["auth"]
    assert auth.priority == 1
    assert "fastapi-postgres" in auth.compatible_bases

    compatible = get_compatible_addons("fastapi-postgres")
    addon_names = {a.name for a in compatible}
    assert addon_names == {"auth", "relations", "redis"}
    print("  PASS: addon registry")


def test_get_available_templates():
    from app.generator.scaffold import get_available_templates

    templates = get_available_templates()
    assert len(templates) >= 1
    names = {t.name for t in templates}
    assert "fastapi-postgres" in names
    print("  PASS: get_available_templates")


# ── 6. submit_plan sentinel parsing ─────────────────────────────


def test_submit_plan_sentinel_parsing():
    from app.agent.base import _parse_manifest_from_sentinel

    manifest = make_bookstore_manifest()
    sentinel = f"__SUBMIT_PLAN__{json.dumps(manifest.to_dict())}"

    parsed = _parse_manifest_from_sentinel(sentinel)
    assert parsed is not None
    assert len(parsed.tasks) == 6
    assert parsed.tasks[0].id == "t1"
    assert parsed.tasks[0].type == "scaffold"
    assert parsed.tasks[-1].type == "docker_up"
    print("  PASS: submit_plan sentinel parsing")


def test_submit_plan_sentinel_invalid():
    from app.agent.base import _parse_manifest_from_sentinel

    parsed = _parse_manifest_from_sentinel("__SUBMIT_PLAN__not-json")
    assert parsed is None
    print("  PASS: submit_plan sentinel handles invalid JSON")


# ── Runner ───────────────────────────────────────────────────────


def main():
    tests = [
        ("Agent class attributes", test_agent_class_attributes),
        ("Tool schema filtering", test_agent_tool_schema_filtering),
        ("Full planning messages", test_full_planning_message_construction),
        ("Delta planning messages", test_delta_planning_message_construction),
        ("Spec round-trip", test_spec_round_trip),
        ("Manifest round-trip", test_manifest_round_trip),
        ("Dependency ordering", test_manifest_dependency_ordering),
        ("Manifest append (delta)", test_manifest_append_tasks),
        ("Template registry lookup", test_template_registry_lookup),
        ("Unknown template error", test_template_registry_unknown_raises),
        ("Addon registry", test_addon_registry),
        ("Available templates", test_get_available_templates),
        ("submit_plan sentinel", test_submit_plan_sentinel_parsing),
        ("submit_plan invalid", test_submit_plan_sentinel_invalid),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name} — {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed:
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    main()
