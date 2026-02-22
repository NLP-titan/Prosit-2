# Track 2: Clarification (Research) Agent

## 1. Purpose of Track 2

The **Clarification Agent** (implemented in `research.py`) is the first agent in a new project. It runs in the **RESEARCH** phase and is responsible only for **structured requirement gathering**. It receives empty or partial `SharedState`, asks targeted follow-up questions, and produces a complete `ProjectSpec`. It must **never** generate code or infrastructure scaffolding.

## 2. Architectural Position

- **Phase**: `Phase.RESEARCH` (orchestrator dispatches to this agent when `current_phase == RESEARCH`).
- **Registration**: Orchestrator registers as `("clarification", "app.agent.agents.clarification", "ClarificationAgent")`. The class lives in `research.py` and is re-exported from `clarification.py` so the orchestrator does not need to be changed.
- **Place in pipeline**: User → ClarificationAgent → (when spec complete and confirmed) → PlanningAgent → …

## 3. Data Flow

```
User message
    → Orchestrator (handle_user_message)
    → _run_research(user_message)
    → ClarificationAgent.run(state, project, user_message=user_message)
    → ReAct loop: LLM → optional ask_user / check_spec_completeness / finalize_spec
    → On finalize_spec: tool returns __FINALIZE_SPEC__{spec_json}
    → BaseAgent sets result.spec = ProjectSpec.from_dict(...)
    → Orchestrator sees result.spec → updates state.spec, transitions to PLANNING
    → state flows to PlanningAgent
```

So: **User → ClarificationAgent → check_spec_completeness → (when complete) summary + user confirmation → finalize_spec → PlanningAgent**.

## 4. Tool Contracts

The agent uses only these three tools (defined in `app.agent.tools` and schemas in `app.agent.prompts._legacy`):

| Tool | Purpose |
|------|--------|
| **ask_user** | Ask a question with optional predefined options. Pauses the agent until the user replies. Parameters: `question` (string), `options` (array of strings). |
| **check_spec_completeness** | Check if the current ProjectSpec has all required fields. Parameters: `spec_json` (string, JSON of ProjectSpec). Returns JSON: `{"complete": bool, "missing": list[str]}`. |
| **finalize_spec** | Submit the complete ProjectSpec and end the research phase. Parameters: `spec_json` (string, full ProjectSpec as JSON). Returns a sentinel that the base agent turns into `result.spec`. |

ProjectSpec schema (exact) is defined in `app.agent.state`: `entities`, `relationships`, `endpoints`, `database`, `auth_required`, `extra_requirements`. Each entity has `name` and `fields` (list of `FieldSpec`: name, type, nullable, unique, default). Each relationship has `entity_a`, `entity_b`, `type` (one_to_one, one_to_many, many_to_many).

## 5. Minimax Configuration

- All LLM calls use **Minimax via OpenRouter**.
- Configuration is in `app.config.settings`:
  - `OPENROUTER_API_KEY`: set in environment (e.g. `.env`).
  - `OPENROUTER_BASE_URL`: `https://openrouter.ai/api/v1`.
  - `OPENROUTER_MODEL`: `minimax/minimax-m2.5` (default).
- The ClarificationAgent uses `settings.OPENROUTER_MODEL` (no other provider). API key is loaded only via config; never hardcoded.

## 6. How to Push to `research-agent` Branch

```bash
git checkout research-agent
git pull origin research-agent
git add .
git commit -m "Track 2: Implement ClarificationAgent"
git push origin research-agent
```

## 7. Testing Instructions

- **Docker Compose**
  - From repo root: `cp .env.example .env`, set `OPENROUTER_API_KEY` in `.env`, then `docker-compose up --build`.
  - Frontend: http://localhost:3000 , Backend: http://localhost:8000.
- **Orchestrator simulation**
  - Create a project via the API or UI, then send a message (e.g. “I want a bookstore API with books and authors”). The RESEARCH phase should run and the ClarificationAgent should respond with questions or a spec summary.
- **Confirm `finalize_spec` triggers**
  - In the chat, provide enough information so the agent can fill all required spec fields (at least one entity with fields; if multiple entities, relationships). When the agent reports the spec is complete and asks for confirmation, reply “yes” (or equivalent). The agent should call `finalize_spec`; the backend should transition to the planning phase and show a phase_transition event (research → planning).
