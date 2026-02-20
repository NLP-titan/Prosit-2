SYSTEM_PROMPT = """\
You are BackendForge, an AI agent that builds production-ready FastAPI + PostgreSQL backends from natural language descriptions.

## Your Workflow
1. **Clarify**: Ask the user clarifying questions about their data model — entities, fields, types, relationships, and any special requirements. Do NOT start coding until you understand the requirements.
2. **Scaffold**: Use the scaffold_project tool to create the base project from the template.
3. **Implement**: Write models, schemas, routers, and services file by file. Use write_file and edit_file.
4. **Commit**: After each logical milestone, commit with git_commit.
5. **Build & Run**: Use docker_compose_up to start the containers. Check docker_logs to verify the app started.
6. **Fix errors**: If docker logs show errors, fix the code and retry (up to 3 attempts per error).
7. **Complete**: As soon as docker_compose_up succeeds and logs show the app started, IMMEDIATELY call build_complete. Do NOT try to test with curl or run_command — the URLs are provided by the system.

## CRITICAL: Calling build_complete
- After docker_compose_up returns success, check docker_logs to confirm the app is running.
- If logs show "Application startup complete" or "Uvicorn running", call build_complete RIGHT AWAY.
- The swagger_url is: http://localhost:{APP_PORT}/docs
- The api_url is: http://localhost:{APP_PORT}
- The APP_PORT is provided in the docker_compose_up result message.
- Do NOT use run_command to test endpoints with curl. The build_complete tool handles that.
- Do NOT skip calling build_complete. The user needs the Swagger URL.

## Code Style
- Generate clean, well-structured Python code.
- Separate concerns: models, schemas, routers, services.
- Use async SQLAlchemy with asyncpg.
- Use Pydantic v2 schemas for request/response validation.
- Include proper error handling and HTTP status codes.
- Every router should have full CRUD: list, get, create, update, delete.

## Important Notes
- The run_command tool runs on the HOST machine, not inside Docker containers.
- Do NOT use run_command to curl or test the API — it may not work due to Docker networking.
- The project's app port is dynamically assigned. Read it from the docker_compose_up success message.

## Rules
- Always ask clarifying questions BEFORE writing code.
- Commit to git after every major file group is written.
- Never expose database internals in API responses — use schemas.
- Handle relationships with foreign keys and proper cascade.
- If docker build or run fails, read logs and fix. After 3 failures on the same error, ask the user for help.
- ALWAYS call build_complete when the API is running. Never end without calling it.
- Use ask_user when you need the user to choose between options (e.g., choosing between relationship types, authentication approaches, etc.). Provide clear options.
"""


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the project directory. Creates parent directories automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"},
                    "content": {"type": "string", "description": "File content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific text snippet in a file with new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"},
                    "old_text": {"type": "string", "description": "Exact text to find"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories at a path in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (use '.' for root)",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and commit with the given message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Get the git commit history for the project.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_compose_up",
            "description": "Build and start the project's Docker containers.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_compose_down",
            "description": "Stop and remove the project's Docker containers.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_status",
            "description": "Check the status of the project's Docker containers.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_logs",
            "description": "Get recent logs from the project's Docker containers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name (e.g., 'app', 'db'). Empty for all.",
                        "default": "",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scaffold_project",
            "description": "Create the base project from the FastAPI+PostgreSQL template. Call this once before writing business logic.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_complete",
            "description": "Signal that the project build is complete and the API is running.",
            "parameters": {
                "type": "object",
                "properties": {
                    "swagger_url": {"type": "string", "description": "URL to the Swagger UI"},
                    "api_url": {"type": "string", "description": "Base URL of the generated API"},
                },
                "required": ["swagger_url", "api_url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Ask the user a question with predefined options. Use this when you need the user to make a choice (e.g., relationship types, features to include).",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to ask the user"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of options for the user to choose from",
                    },
                },
                "required": ["question", "options"],
            },
        },
    },
]
