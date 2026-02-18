from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "minimax/minimax-m2.5"

    PROJECTS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "projects"
    TEMPLATES_DIR: Path = Path(__file__).resolve().parent.parent.parent / "templates"

    # Dynamic port ranges for generated projects
    APP_PORT_START: int = 9001
    DB_PORT_START: int = 5501

    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()

# Ensure projects dir exists
settings.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
