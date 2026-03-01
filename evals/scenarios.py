"""Test scenarios of increasing complexity.

Each scenario defines:
  - A user prompt (what to send over WebSocket)
  - Expected entities with fields (ground truth for schema validation)
  - Expected endpoints (ground truth for endpoint coverage)
  - Answers for ask_user questions (auto-responder)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExpectedField:
    name: str
    type_hint: str  # loose match: "str", "int", "float", "bool", "datetime", "text"


@dataclass
class ExpectedEntity:
    name: str  # e.g. "Todo", "Book"
    fields: list[ExpectedField] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)  # subset that MUST exist


@dataclass
class ExpectedEndpoint:
    method: str   # GET, POST, PUT, DELETE
    path: str     # e.g. "/todos", "/todos/{id}"


@dataclass
class Scenario:
    id: str
    name: str
    complexity: str           # trivial, simple, medium, complex
    prompt: str               # the user message to send
    entities: list[ExpectedEntity] = field(default_factory=list)
    endpoints: list[ExpectedEndpoint] = field(default_factory=list)
    ask_user_answers: list[str] = field(default_factory=list)  # sequential answers
    description: str = ""


# ── Scenario definitions ───────────────────────────────────────

SCENARIOS: list[Scenario] = [
    # ── 1. Trivial: single entity, minimal fields ──────────────
    Scenario(
        id="s1_todo",
        name="Todo API",
        complexity="trivial",
        description="Single entity with 3 fields. Baseline test.",
        prompt="Build me a simple todo API. Each todo has a title (string), description (text), and completed (boolean).",
        entities=[
            ExpectedEntity(
                name="Todo",
                fields=[
                    ExpectedField("title", "str"),
                    ExpectedField("description", "text"),
                    ExpectedField("completed", "bool"),
                ],
                required_fields=["title", "completed"],
            ),
        ],
        endpoints=[
            ExpectedEndpoint("GET", "/todos"),
            ExpectedEndpoint("POST", "/todos"),
            ExpectedEndpoint("GET", "/todos/{id}"),
            ExpectedEndpoint("PUT", "/todos/{id}"),
            ExpectedEndpoint("DELETE", "/todos/{id}"),
        ],
    ),

    # ── 2. Simple: two entities, one-to-many ───────────────────
    Scenario(
        id="s2_blog",
        name="Blog API",
        complexity="simple",
        description="Two entities with a one-to-many relationship.",
        prompt=(
            "Build a blog API. I need Authors (name, email, bio) and Posts "
            "(title, content, published boolean, created_at datetime). "
            "Each post belongs to one author."
        ),
        entities=[
            ExpectedEntity(
                name="Author",
                fields=[
                    ExpectedField("name", "str"),
                    ExpectedField("email", "str"),
                    ExpectedField("bio", "text"),
                ],
                required_fields=["name", "email"],
            ),
            ExpectedEntity(
                name="Post",
                fields=[
                    ExpectedField("title", "str"),
                    ExpectedField("content", "text"),
                    ExpectedField("published", "bool"),
                    ExpectedField("created_at", "datetime"),
                ],
                required_fields=["title", "content"],
            ),
        ],
        endpoints=[
            ExpectedEndpoint("GET", "/authors"),
            ExpectedEndpoint("POST", "/authors"),
            ExpectedEndpoint("GET", "/authors/{id}"),
            ExpectedEndpoint("PUT", "/authors/{id}"),
            ExpectedEndpoint("DELETE", "/authors/{id}"),
            ExpectedEndpoint("GET", "/posts"),
            ExpectedEndpoint("POST", "/posts"),
            ExpectedEndpoint("GET", "/posts/{id}"),
            ExpectedEndpoint("PUT", "/posts/{id}"),
            ExpectedEndpoint("DELETE", "/posts/{id}"),
        ],
    ),

    # ── 3. Medium: three entities, mixed relationships ─────────
    Scenario(
        id="s3_ecommerce",
        name="E-commerce API",
        complexity="medium",
        description="Three entities: categories, products, reviews. One-to-many relationships.",
        prompt=(
            "Build an e-commerce API with three resources: "
            "Categories (name, description), "
            "Products (name, description, price as float, stock_quantity as integer, each product belongs to a category), "
            "and Reviews (rating as integer 1-5, comment as text, each review belongs to a product)."
        ),
        entities=[
            ExpectedEntity(
                name="Category",
                fields=[
                    ExpectedField("name", "str"),
                    ExpectedField("description", "text"),
                ],
                required_fields=["name"],
            ),
            ExpectedEntity(
                name="Product",
                fields=[
                    ExpectedField("name", "str"),
                    ExpectedField("description", "text"),
                    ExpectedField("price", "float"),
                    ExpectedField("stock_quantity", "int"),
                ],
                required_fields=["name", "price"],
            ),
            ExpectedEntity(
                name="Review",
                fields=[
                    ExpectedField("rating", "int"),
                    ExpectedField("comment", "text"),
                ],
                required_fields=["rating"],
            ),
        ],
        endpoints=[
            ExpectedEndpoint("GET", "/categories"),
            ExpectedEndpoint("POST", "/categories"),
            ExpectedEndpoint("GET", "/categories/{id}"),
            ExpectedEndpoint("PUT", "/categories/{id}"),
            ExpectedEndpoint("DELETE", "/categories/{id}"),
            ExpectedEndpoint("GET", "/products"),
            ExpectedEndpoint("POST", "/products"),
            ExpectedEndpoint("GET", "/products/{id}"),
            ExpectedEndpoint("PUT", "/products/{id}"),
            ExpectedEndpoint("DELETE", "/products/{id}"),
            ExpectedEndpoint("GET", "/reviews"),
            ExpectedEndpoint("POST", "/reviews"),
            ExpectedEndpoint("GET", "/reviews/{id}"),
            ExpectedEndpoint("PUT", "/reviews/{id}"),
            ExpectedEndpoint("DELETE", "/reviews/{id}"),
        ],
    ),

    # ── 4. Complex: five entities, multiple relationships ──────
    Scenario(
        id="s4_school",
        name="School Management API",
        complexity="complex",
        description="Five entities with multiple one-to-many relationships.",
        prompt=(
            "Build a school management API. I need: "
            "Departments (name, building), "
            "Teachers (name, email, subject, each teacher belongs to a department), "
            "Courses (title, code, credits as integer, each course belongs to a department and has a teacher), "
            "Students (name, email, enrollment_date as datetime), "
            "and Enrollments (grade as float, enrolled_at as datetime, linking a student to a course)."
        ),
        entities=[
            ExpectedEntity(
                name="Department",
                fields=[
                    ExpectedField("name", "str"),
                    ExpectedField("building", "str"),
                ],
                required_fields=["name"],
            ),
            ExpectedEntity(
                name="Teacher",
                fields=[
                    ExpectedField("name", "str"),
                    ExpectedField("email", "str"),
                    ExpectedField("subject", "str"),
                ],
                required_fields=["name", "email"],
            ),
            ExpectedEntity(
                name="Course",
                fields=[
                    ExpectedField("title", "str"),
                    ExpectedField("code", "str"),
                    ExpectedField("credits", "int"),
                ],
                required_fields=["title", "code"],
            ),
            ExpectedEntity(
                name="Student",
                fields=[
                    ExpectedField("name", "str"),
                    ExpectedField("email", "str"),
                    ExpectedField("enrollment_date", "datetime"),
                ],
                required_fields=["name", "email"],
            ),
            ExpectedEntity(
                name="Enrollment",
                fields=[
                    ExpectedField("grade", "float"),
                    ExpectedField("enrolled_at", "datetime"),
                ],
                required_fields=[],
            ),
        ],
        endpoints=[
            ExpectedEndpoint("GET", "/departments"),
            ExpectedEndpoint("POST", "/departments"),
            ExpectedEndpoint("GET", "/departments/{id}"),
            ExpectedEndpoint("PUT", "/departments/{id}"),
            ExpectedEndpoint("DELETE", "/departments/{id}"),
            ExpectedEndpoint("GET", "/teachers"),
            ExpectedEndpoint("POST", "/teachers"),
            ExpectedEndpoint("GET", "/teachers/{id}"),
            ExpectedEndpoint("PUT", "/teachers/{id}"),
            ExpectedEndpoint("DELETE", "/teachers/{id}"),
            ExpectedEndpoint("GET", "/courses"),
            ExpectedEndpoint("POST", "/courses"),
            ExpectedEndpoint("GET", "/courses/{id}"),
            ExpectedEndpoint("PUT", "/courses/{id}"),
            ExpectedEndpoint("DELETE", "/courses/{id}"),
            ExpectedEndpoint("GET", "/students"),
            ExpectedEndpoint("POST", "/students"),
            ExpectedEndpoint("GET", "/students/{id}"),
            ExpectedEndpoint("PUT", "/students/{id}"),
            ExpectedEndpoint("DELETE", "/students/{id}"),
            ExpectedEndpoint("GET", "/enrollments"),
            ExpectedEndpoint("POST", "/enrollments"),
            ExpectedEndpoint("GET", "/enrollments/{id}"),
            ExpectedEndpoint("PUT", "/enrollments/{id}"),
            ExpectedEndpoint("DELETE", "/enrollments/{id}"),
        ],
    ),
]


def get_scenario(scenario_id: str) -> Scenario | None:
    for s in SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def list_scenario_ids() -> list[str]:
    return [s.id for s in SCENARIOS]
