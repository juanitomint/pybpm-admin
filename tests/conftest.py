"""Shared fixtures for pybpm-admin tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def sync_test_client() -> Iterator[TestClient]:  # type: ignore[misc]
    """Synchronous test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def bearer_token() -> str:
    """Return a mock bearer token used for authenticated requests."""
    return "mock-token-admin"
