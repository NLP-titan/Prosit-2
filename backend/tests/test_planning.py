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
        get_template_dir,
    )

    assert "fastapi-postgres" in TEMPLATE_REGISTRY
    assert "fastapi-mongodb" in TEMPLATE_REGISTRY
    assert "fastapi-mysql" in TEMPLATE_REGISTRY

    fp_template = TEMPLATE_REGISTRY["fastapi-postgres"]
    assert fp_template.name == "fastapi-postgres"
    assert fp_template.path.name == "fastapi-postgres"

    mongo_template = TEMPLATE_REGISTRY["fastapi-mongodb"]
    assert mongo_template.path.name == "fastapi-mongodb"
    assert "auth" in mongo_template.supported_addons
    assert "relations" not in mongo_template.supported_addons

    mysql_template = TEMPLATE_REGISTRY["fastapi-mysql"]
    assert mysql_template.path.name == "fastapi-mysql"
    assert "relations" in mysql_template.supported_addons

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
    assert "fastapi-mongodb" in auth.compatible_bases
    assert "fastapi-mysql" in auth.compatible_bases

    relations = ADDON_REGISTRY["relations"]
    assert "fastapi-postgres" in relations.compatible_bases
    assert "fastapi-mysql" in relations.compatible_bases
    assert "fastapi-mongodb" not in relations.compatible_bases

    compatible_pg = get_compatible_addons("fastapi-postgres")
    assert {a.name for a in compatible_pg} == {"auth", "relations", "redis"}

    compatible_mongo = get_compatible_addons("fastapi-mongodb")
    assert {a.name for a in compatible_mongo} == {"auth", "redis"}

    compatible_mysql = get_compatible_addons("fastapi-mysql")
    assert {a.name for a in compatible_mysql} == {"auth", "relations", "redis"}
    print("  PASS: addon registry")


def test_get_available_templates():
    from app.generator.scaffold import get_available_templates

    templates = get_available_templates()
    assert len(templates) >= 3
    names = {t.name for t in templates}
    assert names == {"fastapi-postgres", "fastapi-mongodb", "fastapi-mysql"}
    print("  PASS: get_available_templates")


# ── 6. Database-to-template mapping ──────────────────────────────


def test_database_to_template_mapping():
    from app.generator.scaffold import get_template_for_database

    assert get_template_for_database("postgresql") == "fastapi-postgres"
    assert get_template_for_database("mongodb") == "fastapi-mongodb"
    assert get_template_for_database("mysql") == "fastapi-mysql"
    print("  PASS: database-to-template mapping")


def test_database_to_template_unknown_raises():
    from app.generator.scaffold import get_template_for_database

    try:
        get_template_for_database("oracle")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "oracle" in str(e)
        assert "postgresql" in str(e)
    print("  PASS: unknown database raises ValueError")


# ── 7. Edge cases — no spec, single entity, empty entities ──────


def test_no_spec_error_guard():
    """Agent should yield error and set result.status='error' when spec is None."""
    import asyncio
    from app.agent.agents.planning import PlanningAgent
    from app.models.project import Project

    agent = PlanningAgent()
    state = SharedState(project_id="test-no-spec", current_phase=Phase.PLANNING)
    state.spec = None

    project = Project(id="test-no-spec", name="test", app_port=9001, db_port=5501)

    events = []
    async def collect():
        async for event in agent.run(state=state, project=project):
            events.append(event)
        return await agent.get_result()

    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(collect())
    loop.close()

    assert len(events) == 1
    assert events[0].type == "error"
    assert "No ProjectSpec" in events[0].data["message"]

    assert result.status == "error"
    assert "No ProjectSpec" in result.error
    print("  PASS: no spec error guard")


def test_single_entity_message_construction():
    """Verify message construction for a single entity with no relationships."""
    spec = ProjectSpec(
        entities=[
            EntitySpec(
                name="Product",
                fields=[
                    FieldSpec(name="name", type="str", nullable=False),
                    FieldSpec(name="price", type="float", nullable=False),
                ],
            ),
        ],
        database="postgresql",
    )
    state = SharedState(project_id="test-single", current_phase=Phase.PLANNING)
    state.spec = spec

    spec_json = json.dumps(state.spec.to_dict(), indent=2)
    content = f"## Project Spec\n```json\n{spec_json}\n```\n\nProduce a complete TaskManifest for this project."

    assert "Product" in content
    assert "relationships" in content
    assert '"relationships": []' in content
    assert "complete TaskManifest" in content
    print("  PASS: single entity message construction")


def test_auth_required_in_spec():
    """Verify auth_required flag is serialized and round-trips correctly."""
    spec = ProjectSpec(
        entities=[
            EntitySpec(
                name="User",
                fields=[FieldSpec(name="email", type="str", nullable=False, unique=True)],
            ),
        ],
        database="postgresql",
        auth_required=True,
    )
    spec_dict = spec.to_dict()
    assert spec_dict["auth_required"] is True

    spec_json = json.dumps(spec_dict)
    assert '"auth_required": true' in spec_json

    spec_back = ProjectSpec.from_dict(json.loads(spec_json))
    assert spec_back.auth_required is True
    print("  PASS: auth_required in spec")


def test_many_to_many_relationship_serialization():
    """Verify many_to_many relationship round-trips correctly."""
    spec = ProjectSpec(
        entities=[
            EntitySpec(name="Student", fields=[FieldSpec(name="name", type="str")]),
            EntitySpec(name="Course", fields=[FieldSpec(name="title", type="str")]),
        ],
        relationships=[
            Relationship(entity_a="Student", entity_b="Course", type="many_to_many"),
        ],
    )
    spec_dict = spec.to_dict()
    assert spec_dict["relationships"][0]["type"] == "many_to_many"

    spec_back = ProjectSpec.from_dict(spec_dict)
    assert spec_back.relationships[0].type == "many_to_many"
    print("  PASS: many_to_many relationship serialization")


# ── 8. Manifest validation helpers ──────────────────────────────

VALID_TASK_TYPES = {"scaffold", "create_models", "create_routes", "docker_up"}
VALID_AGENTS = {"scaffold", "database", "api", "devops"}


def validate_manifest_structure(manifest: TaskManifest) -> list[str]:
    """Validate manifest structure and return list of issues."""
    issues = []
    if not manifest.tasks:
        issues.append("Manifest has no tasks")
        return issues

    task_ids = {t.id for t in manifest.tasks}
    if len(task_ids) != len(manifest.tasks):
        issues.append("Duplicate task IDs detected")

    for task in manifest.tasks:
        if not task.id:
            issues.append(f"Task missing id")
        if task.type not in VALID_TASK_TYPES:
            issues.append(f"Task '{task.id}' has invalid type: {task.type}")
        if task.agent not in VALID_AGENTS:
            issues.append(f"Task '{task.id}' has invalid agent: {task.agent}")
        for dep in task.dependencies:
            if dep not in task_ids:
                issues.append(f"Task '{task.id}' depends on unknown task: {dep}")

    scaffold_tasks = [t for t in manifest.tasks if t.type == "scaffold"]
    if not scaffold_tasks:
        issues.append("No scaffold task found")
    elif scaffold_tasks[0].dependencies:
        issues.append("Scaffold task should have no dependencies")

    docker_tasks = [t for t in manifest.tasks if t.type == "docker_up"]
    if not docker_tasks:
        issues.append("No docker_up task found")

    return issues


def test_manifest_validation_valid():
    manifest = make_bookstore_manifest()
    issues = validate_manifest_structure(manifest)
    assert issues == [], f"Expected no issues, got: {issues}"
    print("  PASS: manifest validation (valid manifest)")


def test_manifest_validation_missing_scaffold():
    manifest = TaskManifest(tasks=[
        Task(id="t1", type="create_models", description="Model", agent="database"),
        Task(id="t2", type="docker_up", description="Docker", agent="devops", dependencies=["t1"]),
    ])
    issues = validate_manifest_structure(manifest)
    assert any("No scaffold" in i for i in issues)
    print("  PASS: manifest validation catches missing scaffold")


def test_manifest_validation_missing_docker():
    manifest = TaskManifest(tasks=[
        Task(id="t1", type="scaffold", description="Scaffold", agent="scaffold"),
        Task(id="t2", type="create_models", description="Model", agent="database", dependencies=["t1"]),
    ])
    issues = validate_manifest_structure(manifest)
    assert any("No docker_up" in i for i in issues)
    print("  PASS: manifest validation catches missing docker_up")


def test_manifest_validation_invalid_type():
    manifest = TaskManifest(tasks=[
        Task(id="t1", type="scaffold", description="Scaffold", agent="scaffold"),
        Task(id="t2", type="invalid_type", description="Bad", agent="database", dependencies=["t1"]),
        Task(id="t3", type="docker_up", description="Docker", agent="devops", dependencies=["t2"]),
    ])
    issues = validate_manifest_structure(manifest)
    assert any("invalid type" in i for i in issues)
    print("  PASS: manifest validation catches invalid task type")


def test_manifest_validation_broken_dependency():
    manifest = TaskManifest(tasks=[
        Task(id="t1", type="scaffold", description="Scaffold", agent="scaffold"),
        Task(id="t2", type="create_models", description="Model", agent="database", dependencies=["t99"]),
        Task(id="t3", type="docker_up", description="Docker", agent="devops", dependencies=["t2"]),
    ])
    issues = validate_manifest_structure(manifest)
    assert any("unknown task" in i for i in issues)
    print("  PASS: manifest validation catches broken dependency")


def test_manifest_validation_duplicate_ids():
    manifest = TaskManifest(tasks=[
        Task(id="t1", type="scaffold", description="Scaffold", agent="scaffold"),
        Task(id="t1", type="create_models", description="Model", agent="database"),
        Task(id="t2", type="docker_up", description="Docker", agent="devops", dependencies=["t1"]),
    ])
    issues = validate_manifest_structure(manifest)
    assert any("Duplicate" in i for i in issues)
    print("  PASS: manifest validation catches duplicate IDs")


def test_task_context_completeness():
    """Verify that a well-formed manifest has populated context dicts."""
    manifest = TaskManifest(tasks=[
        Task(id="t1", type="scaffold", description="Scaffold", agent="scaffold",
             context={"template_name": "fastapi-postgres"}),
        Task(id="t2", type="create_models", description="Create Book model", agent="database",
             dependencies=["t1"],
             context={"entity": "Book", "fields": [{"name": "title", "type": "str"}], "relationships": []}),
        Task(id="t3", type="create_routes", description="Create Book routes", agent="api",
             dependencies=["t2"],
             context={"entity": "Book", "fields": [{"name": "title", "type": "str"}]}),
        Task(id="t4", type="docker_up", description="Docker", agent="devops",
             dependencies=["t3"], context={}),
    ])

    scaffold = manifest.tasks[0]
    assert "template_name" in scaffold.context

    model_task = manifest.tasks[1]
    assert "entity" in model_task.context
    assert "fields" in model_task.context
    assert len(model_task.context["fields"]) > 0

    route_task = manifest.tasks[2]
    assert "entity" in route_task.context
    assert "fields" in route_task.context
    print("  PASS: task context completeness")


# ── 9. submit_plan sentinel parsing ─────────────────────────────


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
        ("DB-to-template mapping", test_database_to_template_mapping),
        ("Unknown DB error", test_database_to_template_unknown_raises),
        ("No spec error guard", test_no_spec_error_guard),
        ("Single entity message", test_single_entity_message_construction),
        ("Auth required in spec", test_auth_required_in_spec),
        ("Many-to-many serialization", test_many_to_many_relationship_serialization),
        ("Manifest validation (valid)", test_manifest_validation_valid),
        ("Missing scaffold", test_manifest_validation_missing_scaffold),
        ("Missing docker_up", test_manifest_validation_missing_docker),
        ("Invalid task type", test_manifest_validation_invalid_type),
        ("Broken dependency", test_manifest_validation_broken_dependency),
        ("Duplicate task IDs", test_manifest_validation_duplicate_ids),
        ("Task context completeness", test_task_context_completeness),
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
