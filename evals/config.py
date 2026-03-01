"""Evaluation suite configuration and constants."""

from __future__ import annotations

# ── Backend connection ──────────────────────────────────────────
API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

# ── Timeouts (seconds) ─────────────────────────────────────────
BUILD_TIMEOUT = 600          # max wait for build_complete event
WS_MESSAGE_TIMEOUT = 120     # max wait for any single WS message
HEALTH_CHECK_TIMEOUT = 30    # per-request timeout when probing generated API
CRUD_REQUEST_TIMEOUT = 15    # per-request timeout for CRUD validation

# ── Retry / polling ────────────────────────────────────────────
HEALTH_RETRIES = 5
HEALTH_RETRY_DELAY = 3       # seconds between health retries

# ── Scoring weights ────────────────────────────────────────────
WEIGHT_COMPLETION = 0.30     # did it reach build_complete?
WEIGHT_SCHEMA = 0.25         # do DB tables / columns match the spec?
WEIGHT_ENDPOINTS = 0.25      # do CRUD endpoints return 2xx?
WEIGHT_BUILD_TIME = 0.10     # faster is better (normalized)
WEIGHT_LLM_ROUNDS = 0.10    # fewer LLM rounds = more efficient

# ── Build-time scoring (seconds) ───────────────────────────────
IDEAL_BUILD_TIME = 120       # 100% score
MAX_BUILD_TIME = 600         # 0% score

# ── LLM rounds scoring ─────────────────────────────────────────
IDEAL_LLM_ROUNDS = 10       # 100% score
MAX_LLM_ROUNDS = 80         # 0% score
