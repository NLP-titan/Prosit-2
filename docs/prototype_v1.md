# BackendForge

## Project Vision

BackendForge is a conversational AI platform that enables non-developers to build production-ready backend APIs through natural language. Users describe what they want, and an AI agent builds a fully dockerized FastAPI backend through an interactive dialogue — handling architecture decisions, code generation, database setup, testing, and documentation automatically.

Think of it as **Claude Code but for backend only**. The long-term architecture is a multi-agent system with research, planning, and implementation phases, orchestrated by a central coordinator. But we're building iteratively — starting with a simple working prototype and expanding from there.

### Full System (Future State)

The complete system will have:
- **Multi-agent architecture**: Orchestrator delegates to specialist agents (database, API routes, auth, config, testing)
- **Three core phases**: Research (understand requirements) → Plan (file-by-file implementation plan) → Implement (code generation with validation)
- **Model routing via OpenRouter**: Expensive models for planning, cheap models for code generation
- **Prompt caching and context compression** for cost efficiency
- **Performance testing** with Locust (load testing, throughput, response time)
- **Hybrid template + dynamic generation**: Predictable scaffolding from templates, business logic generated dynamically

---

## Current Goal: Simple Prototype (Phase 1)

Build a **single-agent** backend builder that can take a user's natural language description and generate a working CRUD FastAPI app with PostgreSQL, fully dockerized, with Swagger docs.

### What the Prototype Does

1. User opens a Next.js web app and describes what they want (e.g., "I want a bookstore API with books, authors, and categories")
2. The agent asks clarifying questions about entities, relationships, and requirements
3. The agent generates a complete FastAPI project with PostgreSQL
4. Everything runs in Docker containers via docker-compose
5. Swagger UI is available for the user to test the API
6. The user can request changes, and the agent edits the codebase
7. All agent work is committed to a local git repo for rollback

### Prototype Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (minimal chat UI) |
| Backend (our app) | Python + FastAPI |
| Generated output | Python + FastAPI projects |
| Database | PostgreSQL in Docker |
| Containerization | Docker + Docker Compose |
| LLM | OpenRouter (start with one model, Minimax M2.5 - "minimax/minimax-m2.5") |
| Version control | Local git per generated project |

NB: You can find my openrouter key in .env

### Project Structure

```
backendforge/
├── frontend/                    # Next.js chat interface
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   ├── components/          # Chat UI components
│   │   └── lib/                 # API client, utilities
│   ├── package.json
│   └── next.config.js
│
├── backend/                     # Our FastAPI server (orchestrates the agent)
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings (OpenRouter key, paths, etc.)
│   │   ├── routers/
│   │   │   ├── chat.py          # WebSocket/SSE endpoint for agent conversation
│   │   │   └── projects.py      # CRUD for user projects (list, get, delete)
│   │   ├── agent/
│   │   │   ├── core.py          # Main agent loop (ReAct: reason → act → observe)
│   │   │   ├── llm.py           # OpenRouter API client
│   │   │   ├── tools.py         # Tool definitions and implementations
│   │   │   ├── prompts.py       # System prompt and tool schemas
│   │   │   └── context.py       # Context/conversation management
│   │   ├── generator/
│   │   │   ├── templates/       # Base project templates (Dockerfile, docker-compose, etc.)
│   │   │   └── scaffold.py      # Template rendering logic
│   │   ├── models/
│   │   │   └── project.py       # Project state model
│   │   └── services/
│   │       ├── docker.py        # Docker compose up/down/status
│   │       ├── git.py           # Git operations (init, commit, log, reset)
│   │       └── project.py       # Project lifecycle management
│   ├── requirements.txt
│   └── Dockerfile
│
├── templates/                   # Cookiecutter-style templates for generated projects
│   └── fastapi-postgres/
│       ├── {{project_name}}/
│       │   ├── app/
│       │   │   ├── main.py
│       │   │   ├── config.py
│       │   │   ├── database.py
│       │   │   ├── models/
│       │   │   ├── schemas/
│       │   │   ├── routers/
│       │   │   └── services/
│       │   ├── alembic/
│       │   ├── alembic.ini
│       │   ├── requirements.txt
│       │   ├── Dockerfile
│       │   └── .env.example
│       └── docker-compose.yml
│
├── projects/                    # Generated user projects live here (gitignored)
├── docker-compose.yml           # Our own app's docker-compose (backend + frontend)
├── .env.example
├── CLAUDE.md
└── README.md
```

### Agent Design (Single Agent for Prototype)

The prototype uses a single ReAct-style agent. The agent loop is:

```
while not done:
    1. Send conversation history + system prompt + tool schemas to LLM
    2. LLM responds with either:
       a. A message to the user (asking a question or explaining what it's doing)
       b. A tool call (read file, write file, run command, etc.)
    3. If tool call: execute the tool, add result to conversation, loop back to 1
    4. If message to user: send to frontend, wait for user response, loop back to 1
    5. Agent decides when the build is "done" and signals completion
```

#### System Prompt Priorities

The agent's system prompt should instruct it to:
- Ask clarifying questions before writing any code (entities, relationships, auth needs, etc.)
- Generate modular, well-structured code (separate models, schemas, routers, services)
- Use the template scaffold first, then fill in dynamic business logic
- Commit to git after every logical milestone with descriptive messages
- Run the docker containers and verify the API works before telling the user it's done
- Handle errors by reading error output and fixing the code

#### Agent Tools

```python
tools = [
    # File operations
    "read_file(path: str) -> str",
    "write_file(path: str, content: str) -> bool",
    "edit_file(path: str, old_text: str, new_text: str) -> bool",
    "list_directory(path: str) -> list[str]",

    # Shell
    "run_command(command: str, cwd: str) -> {stdout, stderr, returncode}",

    # Git
    "git_commit(message: str) -> str",       # returns commit hash
    "git_log() -> list[{hash, message}]",

    # Docker
    "docker_compose_up() -> bool",
    "docker_compose_down() -> bool",
    "docker_status() -> dict",

    # User interaction
    "ask_user(question: str) -> str",         # pauses and waits for user input
    "notify_user(message: str) -> None",      # sends status update, doesn't wait

    # Completion
    "build_complete(swagger_url: str, api_url: str) -> None",  # signals done
]
```

### Template: FastAPI + PostgreSQL Base

The scaffold template generates a project with this structure. The agent fills in the dynamic parts (models, schemas, routes, services).

**What the template provides (static):**
- `main.py` with FastAPI app setup, CORS, lifespan event for DB
- `config.py` with pydantic-settings reading from `.env`
- `database.py` with SQLAlchemy async engine and session setup
- `Dockerfile` for the FastAPI app
- `docker-compose.yml` with app + PostgreSQL services
- `alembic.ini` and `alembic/env.py` for migrations
- `.env.example` with DATABASE_URL, etc.
- `requirements.txt` with fastapi, uvicorn, sqlalchemy, asyncpg, alembic, pydantic-settings

**What the agent generates dynamically:**
- `models/*.py` — SQLAlchemy models based on user's entities
- `schemas/*.py` — Pydantic schemas for request/response
- `routers/*.py` — API route handlers
- `services/*.py` — Business logic layer
- Alembic migration files
- Any additional dependencies

### Frontend (Minimal)

The Next.js frontend for the prototype is intentionally simple:
- A chat interface (left panel) showing the conversation between user and agent
- A status panel (right panel) showing: current project state, file tree, git history
- When build completes: Swagger UI iframe or link, API URL with test instructions
- Ability to see the generated code files
- A "revert" button that maps to git reset

Communication between frontend and backend should use **WebSocket** for real-time streaming of agent messages and status updates.

### Key Implementation Details

**OpenRouter Integration:**
```python
# backend/app/agent/llm.py
# Use OpenRouter's OpenAI-compatible API
# Base URL: https://openrouter.ai/api/v1
# Model: minimax/minimax-m2.5 (for prototype, single model)
# Pass tools in OpenAI function-calling format
# Stream responses for real-time UI updates
```

**Project Isolation:**
- Each user project gets its own directory under `projects/{project_uuid}/`
- Each project has its own git repo, docker-compose, and network
- Docker networks are isolated per project to avoid port conflicts
- Use dynamic port allocation for each project's services

**Error Handling:**
- If generated code fails to run, the agent should:
  1. Read the error from docker logs
  2. Identify the issue
  3. Fix the code
  4. Retry
  5. If it fails 3 times on the same error, ask the user for help

### What NOT to Build in the Prototype

- No multi-agent system (single agent only)
- No model routing (one model via OpenRouter)
- No prompt caching or context compression
- No Locust performance testing
- No auth/JWT support in generated apps
- No MongoDB/Redis/other databases (PostgreSQL only)
- No microservices or modular monolith patterns (simple flat structure only)
- No user authentication for our platform itself
- No persistent storage for conversations (in-memory is fine)

### How to Run

```bash
# 1. Copy .env.example to .env and add your OpenRouter API key
cp .env.example .env

# 2. Start the platform
docker-compose up --build

# 3. Open the frontend
# http://localhost:3000

# 4. Start chatting with the agent to build your API
```

### Definition of Done (Prototype)

The prototype is complete when:
- [ ] User can describe an API in natural language through the chat UI
- [ ] Agent asks clarifying questions about the data model
- [ ] Agent generates a complete FastAPI + PostgreSQL project
- [ ] Generated project runs in Docker containers via docker-compose
- [ ] Swagger UI is accessible and all CRUD endpoints work
- [ ] User can request changes and the agent modifies the code
- [ ] Git commits are made at each milestone with descriptive messages
- [ ] User can view commit history and revert to a previous state
- [ ] Agent handles basic errors (docker build failures, runtime errors) by reading logs and fixing code