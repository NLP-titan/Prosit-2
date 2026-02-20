"""Constants for Track 4 Implementation Agents.

Single source of truth for all magic numbers used across agents, tools,
and the LLM client.
"""

# ---------------------------------------------------------------------------
# LLM loop limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_TOOL_ROUNDS = 20
SCAFFOLD_MAX_TOOL_ROUNDS = 5

# ---------------------------------------------------------------------------
# Output truncation
# ---------------------------------------------------------------------------
TOOL_RESULT_EVENT_MAX_CHARS = 2000
DOCKER_LOG_TAIL_CHARS = 3000
COMMIT_RESULT_PREVIEW_CHARS = 200

# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------
MAX_FILE_WRITE_BYTES = 1_000_000  # 1 MB
MAX_FILE_READ_CHARS = 50_000  # ~50 KB
READ_FILE_TRUNCATION_MSG = "\n... (truncated, {} chars total)"

# ---------------------------------------------------------------------------
# Shell execution
# ---------------------------------------------------------------------------
SHELL_COMMAND_TIMEOUT_SECONDS = 60

# ---------------------------------------------------------------------------
# LLM retry
# ---------------------------------------------------------------------------
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY_SECONDS = 1.0
LLM_RETRY_MAX_DELAY_SECONDS = 15.0
LLM_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# ---------------------------------------------------------------------------
# Code verification
# ---------------------------------------------------------------------------
MAX_VERIFY_ATTEMPTS = 2  # how many times to re-enter the loop to fix errors
VERIFY_TIMEOUT_SECONDS = 10  # timeout for py_compile check

# ---------------------------------------------------------------------------
# Context window management
# ---------------------------------------------------------------------------
ESTIMATED_CHARS_PER_TOKEN = 4
MAX_CONTEXT_TOKENS = 100_000  # conservative limit under typical 128k window
CONTEXT_PRUNE_KEEP_LAST_N = 4  # keep last N message pairs when pruning
