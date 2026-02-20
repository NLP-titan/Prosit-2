from __future__ import annotations

import aiosqlite
from pathlib import Path

from app.config import settings

DB_PATH = settings.ROOT_DIR / "backendforge.db"

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'created',
    app_port INTEGER NOT NULL DEFAULT 0,
    db_port INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    swagger_url TEXT NOT NULL DEFAULT '',
    api_url TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls TEXT,
    tool_call_id TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shared_state (
    project_id TEXT PRIMARY KEY,
    current_phase TEXT NOT NULL DEFAULT 'research',
    spec_json TEXT,
    manifest_json TEXT,
    files_created TEXT DEFAULT '[]',
    errors TEXT DEFAULT '[]',
    updated_at TEXT
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(_CREATE_TABLES)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db
