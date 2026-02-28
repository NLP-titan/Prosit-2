"""Tests for Track 5: ValidationRunner — syntax_check, import_check, validate_project."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.validation import (
    import_check,
    syntax_check,
    validate_project,
)


def test_syntax_check_valid_file(tmp_path):
    valid = tmp_path / "foo.py"
    valid.write_text("def hello():\n    return 42\n")
    passed, err = syntax_check(valid)
    assert passed is True
    assert err is None


def test_syntax_check_invalid_file(tmp_path):
    invalid = tmp_path / "bad.py"
    invalid.write_text("def x(\n")  # missing closing paren and body
    passed, err = syntax_check(invalid)
    assert passed is False
    assert err is not None
    assert "SyntaxError" in err or "syntax" in err.lower()


def test_import_check_resolved(tmp_path):
    py_file = tmp_path / "app.py"
    py_file.write_text("import fastapi\nfrom pydantic import BaseModel\n")
    req = tmp_path / "requirements.txt"
    req.write_text("fastapi==0.100.0\npydantic==2.0.0\n")
    passed, err = import_check(py_file, req)
    assert passed is True
    assert err is None


def test_import_check_unresolved(tmp_path):
    py_file = tmp_path / "app.py"
    py_file.write_text("import nonexistent_package\n")
    req = tmp_path / "requirements.txt"
    req.write_text("fastapi==0.100.0\n")
    passed, err = import_check(py_file, req)
    assert passed is False
    assert err is not None
    assert "nonexistent_package" in err or "Unresolved" in err


def test_import_check_no_requirements(tmp_path):
    py_file = tmp_path / "app.py"
    py_file.write_text("import something\n")
    req = tmp_path / "requirements.txt"
    assert not req.exists()
    passed, err = import_check(py_file, req)
    assert passed is True
    assert err is None


def test_validate_project_mixed(tmp_path):
    (tmp_path / "good.py").write_text("x = 1\n")
    (tmp_path / "bad.py").write_text("def broken(\n")
    result = validate_project(tmp_path)
    assert result["passed"] is False
    assert len(result["errors"]) >= 1
    err = result["errors"][0]
    assert err["type"] == "syntax"
    assert "bad" in err["file"]
    assert err["message"]


def test_validate_project_all_valid(tmp_path):
    (tmp_path / "a.py").write_text("pass\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    result = validate_project(tmp_path)
    assert result["passed"] is True
    assert result["errors"] == []


def test_validate_project_skips_venv(tmp_path):
    (tmp_path / "app.py").write_text("pass\n")
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("def x(\n")  # invalid
    result = validate_project(tmp_path)
    assert result["passed"] is True
    assert result["errors"] == []
