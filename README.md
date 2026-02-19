# BackendForge

Build production-ready backend APIs through natural language. Describe what you want, and an AI agent generates a fully dockerized FastAPI + PostgreSQL project — handling architecture, code generation, database setup, and documentation automatically.

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

## Project Structure

```
backendforge/
├── backend/                 # FastAPI server (orchestrates the AI agent)
│   ├── app/
│   │   ├── main.py          # App entry point, CORS, routers
│   │   ├── config.py        # Settings (OpenRouter key, paths, ports)
│   │   ├── db.py            # SQLite persistence (aiosqlite, WAL mode)
│   │   ├── routers/
│   │   │   ├── chat.py      # WebSocket endpoint for agent conversation
│   │   │   └── projects.py  # Project CRUD endpoints
│   │   ├── agent/
│   │   │   ├── core.py      # ReAct agent loop (reason -> act -> observe)
│   │   │   ├── llm.py       # OpenRouter API client
│   │   │   ├── tools.py     # Tool definitions (file ops, git, docker, etc.)
│   │   │   ├── prompts.py   # System prompt and tool schemas
│   │   │   └── context.py   # Conversation/context management
│   │   ├── generator/
│   │   │   └── scaffold.py  # Template rendering logic
│   │   ├── models/
│   │   │   └── project.py   # Project state model
│   │   └── services/
│   │       ├── docker.py    # Docker compose operations
│   │       ├── git.py       # Git operations
│   │       └── project.py   # Project lifecycle management
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                # Next.js chat interface
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # UI components (chat, file explorer, etc.)
│   │   └── lib/             # API client, WebSocket, state management
│   ├── package.json
│   └── Dockerfile
│
├── templates/               # Cookiecutter-style templates for generated projects
│   └── fastapi-postgres/    # FastAPI + PostgreSQL base template
│
├── projects/                # Generated user projects (gitignored)
├── docker-compose.yml       # Platform docker-compose (backend + frontend)
├── .env.example             # Environment variable template
└── README.md
```

## How It Works

1. **Describe your API** — Open the chat UI and tell the agent what you want (e.g., "I want a bookstore API with books, authors, and categories")
2. **Clarification** — The agent asks follow-up questions about entities, relationships, and requirements
3. **Generation** — The agent scaffolds a FastAPI + PostgreSQL project, writes models, schemas, routes, and services
4. **Docker** — The generated project runs in Docker containers via docker-compose
5. **Test** — Swagger UI is available to test all CRUD endpoints
6. **Iterate** — Request changes through the chat and the agent modifies the code
7. **Version control** — Every milestone is committed to a local git repo; you can view history and revert

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | *(required)* |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | LLM model to use | `minimax/minimax-m2.5` |
| `PROJECTS_DIR` | Directory for generated projects | `../projects` |
| `TEMPLATES_DIR` | Directory for project templates | `../templates` |
| `APP_PORT_START` | Starting port for generated app services | `9001` |
| `DB_PORT_START` | Starting port for generated databases | `5501` |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Backend | Python, FastAPI, aiosqlite |
| AI | OpenRouter (Minimax M2.5) |
| Generated output | FastAPI + PostgreSQL projects |
| Containerization | Docker + Docker Compose |
| Version control | Git (per generated project) |

## License

MIT
