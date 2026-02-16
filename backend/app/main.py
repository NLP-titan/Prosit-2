from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import chat, docker, files, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Path(settings.projects_base_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.projects_base_dir).parent.joinpath("data").mkdir(
        parents=True, exist_ok=True
    )
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(files.router)
app.include_router(docker.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}
