# BackendForge

Build production-ready backend APIs through natural language. Describe what you want, and a multi-agent AI system generates a fully dockerized FastAPI + PostgreSQL project — handling requirements gathering, architecture planning, code generation, database setup, deployment, and documentation automatically.

## Prerequisites

- **Python 3.12+**
- **Node.js 20+**
- **Docker** and **Docker Compose**
- **Git**
- An **OpenRouter API key** ([get one here](https://openrouter.ai/keys))

## Quick Start (Docker Compose)

```bash
# 1. Clone the repo
git clone <repo-url>
cd backendforge

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your OpenRouter API key

# 3. Start everything
docker-compose up --build

# 4. Open the app
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# Health:    http://localhost:8000/health
```

## Local Development

If you prefer running the backend and frontend outside Docker:

### Backend

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

# Install dependencies
python -m pip install -r backend/requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your OpenRouter API key

# Run the backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000` and connects to the backend at `http://localhost:8000`.

### Both running

Open two terminals — one for the backend, one for the frontend. Then open `http://localhost:3000` in your browser.

## Architecture

BackendForge uses a **hybrid multi-agent orchestrator** that manages the full lifecycle through four phases:

```
User Prompt → Research → Planning → Implementation → Validation → Live API
```

### Phases

1. **Research** — The Clarification Agent gathers requirements through a conversational back-and-forth, producing a structured `ProjectSpec` (entities, fields, relationships).

2. **Planning** — The Planning Agent converts the spec into a `TaskManifest` — an ordered, dependency-aware list of tasks (scaffold, create models, create routes, update main, deploy).

3. **Implementation** — The orchestrator dispatches tasks to specialist agents in parallel where dependencies allow:
   - **Scaffold Agent** — renders the base project from a Jinja2 template
   - **Database Agent** — writes SQLAlchemy models, relationships, and migrations
   - **API Agent** — writes Pydantic schemas, FastAPI routers, and service layers

4. **Validation** — The DevOps Agent validates syntax, builds Docker images, starts containers, and runs health checks. On failure, it identifies the error, dispatches the appropriate agent to fix it, and retries automatically (up to 3 attempts).

Phases chain automatically — the user only interacts during research (answering questions) and after completion (testing the API). Mid-build changes are classified (minor edit, additive, breaking) and handled without restarting from scratch.

See [docs/architecture.md](docs/architecture.md) for detailed diagrams and data flow.

## Project Structure

```
backendforge/
├── backend/                     # FastAPI server
│   ├── app/
│   │   ├── main.py              # App entry point, CORS, routers
│   │   ├── config.py            # Settings (API keys, timeouts, ports)
│   │   ├── db.py                # SQLite persistence (aiosqlite, WAL mode)
│   │   ├── routers/
│   │   │   ├── chat.py          # WebSocket endpoint for agent conversation
│   │   │   └── projects.py      # Project CRUD endpoints
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # Hybrid orchestrator — phase management, task dispatch
│   │   │   ├── base.py          # BaseAgent — reusable ReAct loop with retry
│   │   │   ├── state.py         # SharedState, ProjectSpec, TaskManifest
│   │   │   ├── core.py          # Legacy single-agent session (fallback)
│   │   │   ├── llm.py           # OpenRouter client (streaming + non-streaming, retry)
│   │   │   ├── tools.py         # Tool implementations (file ops, git, docker, etc.)
│   │   │   ├── context.py       # ConversationContext + ScopedContext
│   │   │   ├── validation.py    # Pre-deploy syntax and import checks (in-process AST)
│   │   │   ├── agents/          # Specialist agents
│   │   │   │   ├── clarification.py  # Research phase — gathers requirements
│   │   │   │   ├── planning.py       # Planning phase — produces task manifest
│   │   │   │   ├── scaffold.py       # Renders project template
│   │   │   │   ├── database.py       # Writes SQLAlchemy models
│   │   │   │   ├── api.py            # Writes schemas, routers, services
│   │   │   │   └── devops.py         # Validates, builds, deploys Docker
│   │   │   └── prompts/         # Per-agent system prompts
│   │   │       ├── research.py
│   │   │       ├── planning.py
│   │   │       ├── database.py
│   │   │       ├── api.py
│   │   │       └── devops.py
│   │   ├── generator/
│   │   │   └── scaffold.py      # Jinja2 template renderer
│   │   ├── models/
│   │   │   └── project.py       # Project dataclass and ProjectState enum
│   │   └── services/
│   │       ├── docker.py        # Docker compose operations
│   │       ├── git.py           # Git operations
│   │       ├── preview.py       # Database and capabilities preview
│   │       └── project.py       # Project lifecycle management
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                    # Next.js chat interface
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   ├── components/          # UI components (chat, file explorer, etc.)
│   │   └── lib/                 # API client, WebSocket, state management
│   ├── package.json
│   └── Dockerfile
│
├── evals/                       # Automated evaluation suite
│   ├── scenarios.py             # Test cases (trivial → complex)
│   ├── runner.py                # WebSocket conversation driver
│   ├── validator.py             # Post-build API validation
│   ├── metrics.py               # Scoring (schema match, endpoint coverage, etc.)
│   ├── report.py                # JSON + human-readable reports
│   └── run.py                   # CLI entry point
│
├── templates/                   # Cookiecutter-style project templates
│   └── fastapi-postgres/        # FastAPI + PostgreSQL base template
│
├── docs/                        # Architecture and evaluation documentation
├── projects/                    # Generated user projects (gitignored)
├── docker-compose.yml           # Platform docker-compose (backend + frontend)
├── .env.example                 # Environment variable template
└── README.md
```

## How It Works

1. **Describe your API** — Open the chat UI and tell the agent what you want (e.g., "I want a bookstore API with books, authors, and categories")
2. **Clarification** — The Clarification Agent asks follow-up questions about entities, relationships, and requirements, then produces a structured specification
3. **Planning** — The Planning Agent generates an ordered task manifest with dependency tracking
4. **Code generation** — Specialist agents (Scaffold, Database, API) execute tasks in parallel where possible, with shared context seeding to avoid redundant file reads
5. **Validation and deployment** — The DevOps Agent validates syntax, builds Docker images, starts containers, and verifies health. Errors trigger automatic fixes and retries
6. **Test** — Swagger UI is available to test all CRUD endpoints
7. **Iterate** — Request changes mid-build or after completion. Changes are classified and handled appropriately (minor edits, additive features, or full re-plans)
8. **Version control** — Every milestone is committed to a local git repo; you can view history and revert

## Evaluation

BackendForge includes an automated evaluation suite that runs end-to-end tests against a live backend instance.

```bash
# Start the backend first
cd backend && python -m uvicorn app.main:app --port 8000

# Run all scenarios (trivial → complex)
python -m evals.run

# Run a specific scenario
python -m evals.run s1_todo

# Verbose with no cleanup (keep generated projects)
python -m evals.run -v --no-cleanup
```

The eval creates real projects, sends prompts over WebSocket, auto-responds to clarification questions, waits for build completion, then validates the generated API by probing OpenAPI schemas and CRUD endpoints. Produces a scored report with per-scenario breakdowns.

See [docs/evaluation.md](docs/evaluation.md) for full methodology and scoring details.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | *(required)* |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | LLM model to use | `minimax/minimax-m2.5` |
| `PUBLIC_HOST` | Hostname for generated Swagger/API URLs | `localhost` |
| `PROJECTS_DIR` | Directory for generated projects | `../projects` |
| `TEMPLATES_DIR` | Directory for project templates | `../templates` |
| `APP_PORT_START` | Starting port for generated app services | `9001` |
| `DB_PORT_START` | Starting port for generated databases | `5501` |
| `LLM_TIMEOUT` | Per-request LLM timeout (seconds) | `120` |
| `LLM_MAX_RETRIES` | Retry count for transient LLM failures | `3` |
| `AGENT_TIMEOUT` | Max time for a single agent run (seconds) | `300` |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Backend | Python, FastAPI, aiosqlite |
| AI | OpenRouter (Minimax M2.5), multi-agent orchestration |
| Generated output | FastAPI + PostgreSQL projects |
| Containerization | Docker + Docker Compose |
| Evaluation | Custom end-to-end suite (WebSocket + HTTP probing) |
| Version control | Git (per generated project) |
| CI/CD | GitHub Actions (DigitalOcean deployment) |

## License

MIT
