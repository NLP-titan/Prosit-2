import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy libs
for _lib in ("httpx", "openai", "httpcore"):
    logging.getLogger(_lib).setLevel(logging.WARNING)
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import projects, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="BackendForge", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
