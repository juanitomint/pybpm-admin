"""Shared fixtures and helpers for pybpm-admin integration tests."""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator, Iterator
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from main import app

# --------------------------------------------------------------------------- #
# Mock transport that stands in for pybpm-api                                 #
# --------------------------------------------------------------------------- #


def _default_auth_me_response() -> dict:
    """Default /auth/me response — simulates admin user."""
    return {
        "id": 1,
        "username": "admin",
        "email": "admin@pybpm.local",
        "roles": ["admin"],
    }


def _default_get_models_response() -> list[dict]:
    """Default /repository/get_models response — a few sample models."""
    return [
        {
            "idwf": "test-01",
            "name": "Test Model 01",
            "folder": "General",
            "data": {"properties": {"name": "Test Model 01"}},
        },
        {
            "idwf": "test-loop",
            "name": "Test Loop Flow",
            "folder": "General",
            "data": {"properties": {"name": "Test Loop Flow"}},
        },
        {
            "idwf": "subproc-02",
            "name": "Subprocess 02",
            "folder": "HR",
            "data": {"properties": {"name": "Subprocess 02"}},
        },
    ]


def _build_mock_tree(models: list[dict]) -> list[dict]:
    """Build the same ExtJS tree structure that pybpm-api /repository/get_tree2/json produces.

    Replicates legacy Admin::get_tree2(): flat {folder/idwf => "name [idwf]"} →
    explodeTree(delimiter='/') → convert_to_ext().
    """
    if not models:
        models = _default_get_models_response()
    m_arr: dict[str, str] = {}
    for m in models:
        folder = (m.get("folder") or "General").rstrip("/") + "/"
        idwf = m.get("idwf", "")
        name = (
            (m.get("data") or {})
            .get("properties", {})
            .get("name", m.get("name", f"Model {idwf}"))
        )
        m_arr[f"{folder}{idwf}"] = f"{name} [{idwf}]"

    def _explode(arr, delim="/"):
        if not isinstance(arr, dict):
            return False
        out: dict = {}
        for k in sorted(arr.keys()):
            v = arr[k]
            parts = [p for p in str(k).split(delim) if p]
            leaf = parts.pop()
            parent = out
            for p in parts:
                parent.setdefault(p, {})
                parent = parent[p]
            parent[leaf] = v

        def _sort(d):
            if isinstance(d, dict):
                return {k: _sort(v) for k, v in sorted(d.items())}
            return d

        return _sort(out)

    tree_data = _explode(m_arr)

    def _convert_ext(arr):
        rtn = []
        for key, value in arr.items():
            if isinstance(value, dict):
                children_flat = _convert_ext(
                    {k: value[k] for k in sorted(value.keys())}
                )
                children = []
                for c in children_flat:
                    children.extend(c) if isinstance(c, list) else children.append(c)
                rtn.append(
                    {
                        "text": key,
                        "leaf": False,
                        "cls": "folder",
                        "expanded": True,
                        "children": children,
                    }
                )
            else:
                rtn.append(
                    {"id": str(key), "text": value, "leaf": True, "iconCls": None}
                )
        return rtn

    return _convert_ext(tree_data)


def build_mock_transport(
    auth_me_response: dict | None = None,
    get_models_response: list[dict] | None = None,
) -> httpx.MockTransport:
    """Build a mock transport that returns canned pybpm-api responses.

    Handles paths with or without the /api/v1 prefix (both forms appear in
    tests depending on how PYBPM_API_URL is configured). Also handles both
    /repository/add/{idwf} and bare /add/{idwf} path forms since admin_router's
    _call_backend strips the repository prefix when proxying to pybpm-api.
    """

    def _strip_prefix(path: str) -> str:
        """Strip the /api/v1 prefix used by pybpm-api when called from admin_router."""
        if path.startswith("/api/v1"):
            return path[7:]  # remove leading "/api/v1"
        return path

    def handler(request: httpx.Request) -> httpx.Response:
        raw_path = request.url.path
        path = _strip_prefix(raw_path)
        method = request.method.lower()

        # --- /auth/me (token validation) ----------------------------------- #
        if path == "/auth/me" and method == "get":
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                return httpx.Response(
                    401, json={"detail": "Missing authorization token"}
                )
            return httpx.Response(
                200, json=auth_me_response or _default_auth_me_response()
            )

        # --- /auth/token (login) ------------------------------------------- #
        if path == "/auth/token" and method == "post":
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                form_data = parse_qs((request.content or b"").decode())
                username = (form_data.get("username") or [""])[0]
                password = (form_data.get("password") or [""])[0]

                # Accept admin/admin or any non-empty credentials for tests
                if username and password:
                    return httpx.Response(
                        200,
                        json={
                            "access_token": f"mock-token-{username}",
                            "token_type": "bearer",
                        },
                    )
            return httpx.Response(401, json={"detail": "Invalid credentials"})

        # Normalise: strip optional "/repository/" prefix so handlers match both
        # direct admin_router calls (e.g. /api/v1/repository/get_models) and
        # browser-JS proxy routes that call without it (e.g. /add/{idwf}).
        norm = (
            ("/" + path[len("/repository/") :])
            if path.startswith("/repository/")
            else path
        )

        # --- /get_models (used by get_tree, new_model_form) ---------------- #
        if norm == "/get_models" and method == "get":
            return httpx.Response(
                200, json=get_models_response or _default_get_models_response()
            )

        # --- /get_tree2/json ------------------------------------------------- #
        if path == "/repository/get_tree2/json" and method == "get":
            return httpx.Response(
                200,
                content=json.dumps(_build_mock_tree(get_models_response)),
                headers={"content-type": "application/json"},
            )

        # --- /load/model/{idwf} -------------------------------------------- #
        if norm.startswith("/load/model/") and method == "get":
            idwf = norm.split("/")[-1]
            sample: dict[str, Any] = {
                "idwf": idwf,
                "name": f"Model {idwf}",
                "folder": "General",
                "data": {"properties": {"name": f"Model {idwf}"}},
                "svg": "<svg></svg>",
            }
            return httpx.Response(200, json=sample)

        # --- /add/{idwf} (used by admin_router's proxy routes) ------------- #
        if norm.startswith("/add/") and method == "post":
            idwf = norm.split("/")[-1]
            return httpx.Response(
                200, json={"ok": True, "msg": f"Created model {idwf}"}
            )

        # --- /update_folder ------------------------------------------------ #
        if norm == "/update_folder" and method == "post":
            return httpx.Response(200, json={"ok": True})

        # --- /delete (DELETE) ---------------------------------------------- #
        if norm == "/delete" and method == "delete":
            content = request.content or b"{}"
            body = json.loads(content)
            idwf = body.get("idwf", "unknown")
            return httpx.Response(200, json={"ok": True, "msg": f"Deleted {idwf}"})

        # --- /duplicate (POST) --------------------------------------------- #
        if norm == "/duplicate" and method == "post":
            return httpx.Response(200, json={"ok": True, "msg": "Duplicate OK"})

        # --- /import (POST) ------------------------------------------------ #
        if norm == "/import" and method == "post":
            return httpx.Response(200, json={"ok": True, "msg": "Import OK"})

        # --- get_shapes/model/{idwf} --------------------------------------- #
        if norm.startswith("/get_shapes/model/") and method == "get":
            return httpx.Response(200, json={})

        # --- /svg/{idwf} --------------------------------------------------- #
        if path.startswith("/svg/") and method == "get":
            idwf = path.split("/")[-1]
            return httpx.Response(
                200,
                content=b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
                headers={"content-type": "image/svg+xml"},
            )

        # Default: 404 for unknown backend routes
        return httpx.Response(
            404, json={"detail": f"Mock pybpm-api not found: {method} {path}"}
        )

    return httpx.MockTransport(handler)


# --------------------------------------------------------------------------- #
# Helpers — monkey-patch admin_router to use mock transport                   #
# --------------------------------------------------------------------------- #


@contextlib.contextmanager
def _patch_admin_backend(mock_transport: httpx.MockTransport) -> Iterator[None]:
    """Temporarily replace httpx.AsyncClient with one using the given mock
    transport, and restore on exit."""

    original = httpx.AsyncClient

    class MockedAsyncClient(httpx.AsyncClient):  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any):  # type: ignore[misc]
            kwargs["transport"] = mock_transport
            super().__init__(*args, **kwargs)

    httpx.AsyncClient = MockedAsyncClient  # type: ignore[assignment]
    try:
        yield
    finally:
        httpx.AsyncClient = original  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Fixtures — client + mock transport                                          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def mock_transport() -> httpx.MockTransport:
    """Per-test mock transport for pybpm-api."""
    return build_mock_transport()


@pytest_asyncio.fixture
async def async_client(
    mock_transport: httpx.MockTransport,
) -> AsyncIterator[httpx.AsyncClient]:  # type: ignore[misc]
    """Async test client backed by the ASGI app with mock transport."""
    with _patch_admin_backend(mock_transport):
        transport = httpx.ASGITransport(app=app)
        async_client = httpx.AsyncClient(transport=transport)
        yield async_client
        await async_client.aclose()


@pytest.fixture
def sync_test_client() -> Iterator[TestClient]:  # type: ignore[misc]
    """Synchronous test client for non-async tests.

    Uses Starlette's TestClient (default backend). Patches only admin_router's
    reference to httpx.AsyncClient so outbound calls to pybpm-api go through the
    mock transport — without affecting the ASGI transport used by TestClient itself.
    """
    import admin_router as ar

    original = ar.httpx.AsyncClient  # type: ignore[attr-defined]

    class MockedAsyncClient(ar.httpx.AsyncClient):  # type: ignore[misc,attr-defined]
        def __init__(self, *args: Any, **kwargs: Any):  # type: ignore[misc]
            kwargs["transport"] = build_mock_transport()
            super().__init__(*args, **kwargs)

    ar.httpx.AsyncClient = MockedAsyncClient  # type: ignore[attr-defined]
    try:
        client = TestClient(app)
        yield client
    finally:
        ar.httpx.AsyncClient = original  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


@pytest.fixture
def bearer_token() -> str:
    """Return a mock bearer token used for authenticated requests."""
    return "mock-token-admin"


@pytest.fixture
def auth_headers(bearer_token: str) -> dict[str, str]:
    """Standard Authorization header with the mock bearer token.

    Note: This is kept for backward compatibility with older test patterns.
    The production /admin endpoint uses a session cookie (bpm_session), not
    the Authorization header directly — auth_shim.js reads the cookie and
    injects it as Bearer on all Ext.Ajax requests.
    """
    return {"Authorization": f"Bearer {bearer_token}"}


@pytest.fixture
def session_headers(bearer_token: str) -> dict[str, str]:
    """Session-cookie headers — mirrors what auth_shim.js sends in production."""
    return {"Cookie": f"bpm_session={bearer_token}"}
