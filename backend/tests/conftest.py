"""Pytest configuration. Enables pytest-asyncio for async tests."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as an async test (pytest-asyncio)")
