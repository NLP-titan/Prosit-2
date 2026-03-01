# BackendForge — Evaluation Suite

## Overview

The evaluation suite (`evals/`) is an automated end-to-end testing framework that measures how well BackendForge generates working APIs from natural language prompts. It runs real conversations against a live backend instance, validates the generated APIs structurally, and produces scored reports.

This is **not** a unit test suite. It exercises the full pipeline: LLM calls, code generation, Docker build, deployment, and API functionality.

---

## How It Works

```
┌──────────────┐     REST: POST /projects       ┌──────────────────┐
│              │ ──────────────────────────────→  │                  │
│  Eval Runner │     WebSocket: send prompt       │  BackendForge    │
│              │ ──────────────────────────────→  │  Backend         │
│  (evals/)    │     WebSocket: stream events     │  (localhost:8000) │
│              │ ←──────────────────────────────  │                  │
└──────┬───────┘                                  └────────┬─────────┘
       │                                                   │
       │  HTTP: probe CRUD endpoints                       │ Docker: build & run
       │ ──────────────────────────────→  ┌────────────────┴──┐
       │  HTTP: GET /openapi.json         │  Generated API     │
       │ ←──────────────────────────────  │  (localhost:9001+) │
       │                                  └───────────────────┘
       ▼
  JSON report + terminal summary
```

### Step-by-Step Flow

1. **Project Creation** — The runner creates a real project via `POST /projects`, receiving a project ID and allocated ports.

2. **WebSocket Conversation** — The runner connects to `ws://localhost:8000/ws/chat/{project_id}` and sends the scenario's prompt as a user message. This triggers the full orchestrator pipeline: research, planning, code generation, Docker deployment.

3. **Event Collection** — The runner listens to all WebSocket events (`agent_message_*`, `tool_call_*`, `build_complete`, `ask_user`, `error`, etc.) and logs them for analysis.

4. **Auto-Responses** — When the agent sends an `ask_user` event (a clarification question), the runner responds automatically using pre-defined answers from the scenario, or falls back to the first suggested option, or "yes". This simulates the user's side of the conversation — **not** the LLM's.

5. **Completion Detection** — The runner waits for a `build_complete` event (indicating the API is deployed and healthy) or a timeout (default: 10 minutes).

6. **Post-Build Validation** — If the build succeeds, the runner validates the generated API by:
   - Checking the health endpoint
   - Fetching the OpenAPI spec for schema analysis
   - Probing each expected CRUD endpoint with real HTTP requests

7. **Scoring** — Metrics are computed and weighted into a final score per scenario.

8. **Reporting** — A JSON results file and human-readable terminal summary are generated.

---

## Test Scenarios

Each scenario defines a prompt, expected entities with fields, and expected CRUD endpoints. Scenarios increase in complexity:

| ID | Name | Complexity | Entities | Description |
|----|------|-----------|----------|-------------|
| `s1_todo` | Todo API | Trivial | 1 | Single entity, 3 fields. Baseline test. |
| `s2_blog` | Blog API | Simple | 2 | Authors + Posts with one-to-many relationship. |
| `s3_ecommerce` | E-commerce API | Medium | 3 | Categories, Products, Reviews with chained relationships. |
| `s4_school` | School Management API | Complex | 5 | Departments, Teachers, Courses, Students, Enrollments. |

Scenarios are defined in `evals/scenarios.py` as dataclasses. Adding a new scenario means appending a `Scenario` object to the `SCENARIOS` list.

---

## Evaluation Methodology

### What Is Measured

The evaluation uses **structural validation** — no LLM-as-judge. Everything is verified programmatically by inspecting the generated API's actual behavior and OpenAPI specification.

#### 1. Completion (Weight: 30%)

Binary pass/fail: did the system emit a `build_complete` event within the timeout? This means the code was generated, Docker containers were built and started, and the health check passed.

- **1.0** — `build_complete` received
- **0.0** — timeout, error, or agent stopped

#### 2. Schema Match (Weight: 25%)

Measures whether the generated database models contain the expected fields.

**How it works:**
- Fetches `/openapi.json` from the generated API
- For each expected entity (e.g. "Todo"), finds the matching schema in the OpenAPI spec using normalized name matching (e.g. "Todo" matches "TodoBase", "TodoCreate", "TodoSchema")
- Compares expected fields against actual schema properties
- Auto-generated fields (`id`, `created_at`, `updated_at`) and foreign keys (`*_id`) are excluded from comparison

**Score:** `fields_found / fields_expected` averaged across all entities.

#### 3. Endpoint Coverage (Weight: 25%)

Measures whether the expected CRUD endpoints actually respond.

**How it works:**
- Sends real HTTP requests to each expected endpoint
- Considers an endpoint "covered" based on its method:
  - `GET /resources` — expects 200 (empty list is fine)
  - `GET /resources/{id}` — expects 200 or 404 (no data yet is fine)
  - `POST /resources` — expects 200, 201, or 422 (validation error = endpoint exists)
  - `PUT /resources/{id}` — expects 200, 204, 404, or 422
  - `DELETE /resources/{id}` — expects 200, 204, 404, or 422

**Score:** `successful_endpoints / total_expected_endpoints`.

#### 4. Build Time (Weight: 10%)

Measures generation speed. Scored on a linear scale:

- **120s or less** → 1.0 (ideal)
- **600s or more** → 0.0 (worst)
- Linear interpolation between

#### 5. LLM Efficiency (Weight: 10%)

Measures how many tool calls (proxy for LLM rounds) were needed. Fewer rounds = more efficient prompts and context seeding.

- **10 tool calls or fewer** → 1.0 (ideal)
- **60 tool calls or more** → 0.0 (worst)
- Linear interpolation between

### What Is NOT Measured

- **Code quality** — no linting, style, or best-practice checks
- **Relationship correctness** — field presence is checked, but not whether foreign keys actually work
- **Error handling** — no verification of validation messages, error responses
- **Security** — no auth, injection, or access control testing
- **Performance** — no load testing on the generated API

---

## Scoring

Each scenario receives a weighted final score:

```
final_score = 0.30 * completion
            + 0.25 * schema_match
            + 0.25 * endpoint_coverage
            + 0.10 * build_time_score
            + 0.10 * llm_efficiency_score
```

Letter grades are assigned:

| Score | Grade |
|-------|-------|
| >= 90% | A |
| >= 80% | B |
| >= 70% | C |
| >= 60% | D |
| < 60% | F |

Aggregate metrics are also computed across all scenarios, with breakdowns by complexity level.

---

## Usage

The backend must be running on `localhost:8000` before starting the eval.

```bash
# Start the backend
cd backend && python -m uvicorn app.main:app --port 8000

# Run all scenarios
python -m evals.run

# Run a specific scenario
python -m evals.run s1_todo

# Run multiple specific scenarios
python -m evals.run s1_todo s2_blog

# Keep generated projects alive for manual inspection
python -m evals.run --no-cleanup

# Verbose logging (shows every WS event and HTTP probe)
python -m evals.run -v

# Custom output path for JSON report
python -m evals.run -o results/my_eval.json
```

### Output

**Terminal:** A human-readable summary with per-scenario pass/fail, scores, and failed endpoint/schema details.

**JSON:** A detailed report saved to `evals/results/eval_{timestamp}.json` containing:
- Aggregate metrics (completion rate, averages by complexity)
- Per-scenario metrics (all scores, schema details, endpoint results)

### Example Output

```
============================================================
  BackendForge Evaluation Report
============================================================

  Overall Score: 72.5%  (Grade: C)
  Completion Rate: 75% (3/4)
  Avg Build Time: 245s
  Avg Tool Calls: 32
  Avg Schema Match: 85.0%
  Avg Endpoint Coverage: 80.0%

  By Complexity:
    trivial : 1/1 completed, avg score 95.0%, avg build 120s
    simple  : 1/1 completed, avg score 82.0%, avg build 200s
    medium  : 1/1 completed, avg score 68.0%, avg build 415s
    complex : 0/1 completed, avg score 15.0%, avg build 0s

------------------------------------------------------------
  Scenario Details
------------------------------------------------------------

  [PASS] Todo API (trivial)
    Score: 95.0%  |  Build: 120s  |  Tools: 15
    Schema: 100%  |  Endpoints: 100%

  [PASS] Blog API (simple)
    Score: 82.0%  |  Build: 200s  |  Tools: 28
    Schema: 83%  |  Endpoints: 90%
    Post: missing [created_at]
    Failed endpoints:
      PUT /posts/{id} -> 500

  [FAIL] School Management API (complex)
    Score: 15.0%  |  Build: 600s  |  Tools: 55
    Schema: 0%  |  Endpoints: 0%
    Error: Build did not complete within 600s

============================================================
```

---

## File Structure

```
evals/
├── __init__.py
├── __main__.py        # python -m evals entry point
├── config.py          # timeouts, scoring weights, thresholds
├── scenarios.py       # test case definitions (prompts, expected entities/endpoints)
├── runner.py          # WebSocket conversation driver
├── validator.py       # post-build API validation (OpenAPI + HTTP probing)
├── metrics.py         # metric computation and weighted scoring
├── report.py          # JSON + human-readable report generation
├── run.py             # CLI entry point
└── results/           # generated JSON reports (gitignored)
```

---

## Adding New Scenarios

Add a new `Scenario` to the `SCENARIOS` list in `evals/scenarios.py`:

```python
Scenario(
    id="s5_library",
    name="Library API",
    complexity="medium",
    prompt="Build a library management API with Books, Members, and Loans...",
    entities=[
        ExpectedEntity(
            name="Book",
            fields=[
                ExpectedField("title", "str"),
                ExpectedField("isbn", "str"),
            ],
            required_fields=["title"],
        ),
        # ...
    ],
    endpoints=[
        ExpectedEndpoint("GET", "/books"),
        ExpectedEndpoint("POST", "/books"),
        # ...
    ],
    ask_user_answers=["yes", "no"],  # optional pre-defined answers
)
```

---

## Configuration

All tunable parameters are in `evals/config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BUILD_TIMEOUT` | 600s | Max wait for build_complete |
| `WS_MESSAGE_TIMEOUT` | 120s | Max wait for any single WS message |
| `HEALTH_RETRIES` | 5 | Health check attempts before giving up |
| `WEIGHT_COMPLETION` | 0.30 | Score weight for build completion |
| `WEIGHT_SCHEMA` | 0.25 | Score weight for schema match |
| `WEIGHT_ENDPOINTS` | 0.25 | Score weight for endpoint coverage |
| `WEIGHT_BUILD_TIME` | 0.10 | Score weight for build speed |
| `WEIGHT_LLM_ROUNDS` | 0.10 | Score weight for LLM efficiency |
| `IDEAL_BUILD_TIME` | 120s | Build time that scores 100% |
| `MAX_BUILD_TIME` | 600s | Build time that scores 0% |
