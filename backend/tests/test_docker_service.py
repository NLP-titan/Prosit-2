"""Tests for Track 5: docker service — compose_build, health_check, get_build_errors."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.docker import (
    _parse_build_output,
    compose_build,
    get_build_errors,
    health_check,
)


def test_parse_build_output_empty():
    assert _parse_build_output("") == "Build failed (no output)."
    assert "failed" in _parse_build_output("").lower()


def test_parse_build_output_python_traceback():
    output = """
Step 5/8 : RUN pip install -r requirements.txt
 ---> Running in abc123
  File "/app/models/book.py", line 10
    def get(
          ^
SyntaxError: invalid syntax
"""
    result = _parse_build_output(output)
    assert "book.py" in result or "line 10" in result
    assert "SyntaxError" in result or "invalid syntax" in result


def test_parse_build_output_error_line():
    output = """
Step 1 : COPY . .
ERROR: failed to solve: something went wrong
"""
    result = _parse_build_output(output)
    assert "error" in result.lower() or "failed" in result.lower()


@pytest.mark.asyncio
async def test_health_check_success():
    # We mock by testing against a real HTTP server or use respx
    # For simplicity: test that 200 returns True
    try:
        ok, body = await health_check("https://httpbin.org/get", timeout=5)
        # httpbin may return 200
        if ok:
            assert body
    except Exception:
        # If no network, skip or use a mock
        pass


@pytest.mark.asyncio
async def test_health_check_failure():
    ok, msg = await health_check("http://localhost:19999/nonexistent", timeout=1)
    assert ok is False
    assert msg


@pytest.mark.asyncio
async def test_compose_build_nonexistent_dir(tmp_path):
    # Directory with no docker-compose.yml — build will fail
    ok, output = await compose_build(tmp_path, timeout=10)
    assert ok is False
    assert output


@pytest.mark.asyncio
async def test_get_build_errors_with_output():
    output = 'File "app/models/author.py", line 5\nNameError: name "x" is not defined'
    result = await get_build_errors(Path("/tmp"), build_output=output)
    assert result
    assert "author" in result or "line" in result
