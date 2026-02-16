from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-sonnet-4"

    # Paths
    projects_base_dir: str = str(Path(__file__).parent.parent / "projects")
    database_url: str = f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'data' / 'backendforge.db'}"
    # Host path for Docker build context (set via DOCKER_HOST_PROJECT_DIR env var)
    # When running inside Docker, the daemon needs the host path, not the container path
    docker_host_project_dir: str = ""

    # App
    app_name: str = "Kruya-Jenjen BackendForge"
    debug: bool = True
    max_agent_iterations: int = 25
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
