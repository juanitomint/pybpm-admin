"""PyBPM Editor — FastAPI application entry point.

Serves:
- Static Oryx editor assets (JS/CSS/images) at /static
- Standalone login page at /login
- Model Browser admin API endpoints at /admin/*
- The editor shell page (index.html) at /
- The Model Browser UI at /admin (requires authentication)
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from admin_router import router as admin_router
from config import Config

_base_dir = Path(__file__).resolve().parent
_index_html = (_base_dir / "index.html").read_text(encoding="utf-8")
_admin_html = (_base_dir / "admin.html").read_text(encoding="utf-8")
_login_html = (_base_dir / "login.html").read_text(encoding="utf-8")

SESSION_COOKIE = "bpm_session"


def _user_has_session(request: Request) -> bool:
    """Check if the user has a valid session cookie."""
    return SESSION_COOKIE in request.cookies


async def _authenticate_user(username: str, password: str) -> dict | None:
    """Attempt to authenticate against pybpm-api. Returns token data on success, None otherwise."""
    auth_url = Config.PYBPM_API_URL.rstrip("/") + "/auth/token"
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                auth_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code == 200:
                return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    return None


def create_app() -> FastAPI:
    app = FastAPI(
        title="PyBPM Editor",
        version="0.1.0",
        openapi_url="/openapi.json",
    )

    # CORS — allow pybpm-api origin for Oryx editor save/load calls, and same-origin admin calls.
    origins = [
        f"http://localhost:{Config.PORT}",
        "http://localhost:5000",  # pybpm-api dev server
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files (Oryx editor assets from legacy codebase)
    if os.path.isdir(Config.STATIC_ROOT):
        app.mount("/static", StaticFiles(directory=Config.STATIC_ROOT), name="static")

    # Include admin router (/admin/* endpoints — Model Browser API)
    app.include_router(admin_router)

    @app.get("/", response_class=HTMLResponse)
    async def editor_index():
        """Serve the Oryx editor shell page."""
        return HTMLResponse(content=_index_html)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Standalone login form. If already authenticated, redirect to admin or ?next= URL."""
        if _user_has_session(request):
            next_url = request.query_params.get("next") or "/admin"
            return RedirectResponse(url=next_url)
        return HTMLResponse(content=_login_html)

    @app.post("/login", response_model=None)
    async def login_submit(
        username: str = Form(...),
        password: str = Form(...),
        request: Request = None,  # type: ignore[assignment]
    ):
        """Authenticate user against pybpm-api. On success set session cookie and redirect."""
        auth_data = await _authenticate_user(username, password)

        if auth_data is None or "access_token" not in auth_data:
            next_url = request.query_params.get("next") or "/admin"
            return RedirectResponse(
                url=f"/login?error=Invalid+username+or+password&next={next_url}",
                status_code=302,
            )

        # Set session cookie with the JWT token (signed client-side for simplicity)
        response = RedirectResponse(url="/admin", status_code=302)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=auth_data["access_token"],
            httponly=True,
            secure=False,  # set True in production with HTTPS
            samesite="lax",
            max_age=86400 * 7,  # 1 week
        )

        next_url = request.query_params.get("next")
        if next_url:
            response.delete_cookie(SESSION_COOKIE)
            response.set_cookie(
                key=SESSION_COOKIE,
                value=auth_data["access_token"],
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=86400 * 7,
            )
            response = RedirectResponse(url=next_url, status_code=302)
            response.set_cookie(
                key=SESSION_COOKIE,
                value=auth_data["access_token"],
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=86400 * 7,
            )

        return response

    @app.get("/admin")
    async def admin_editor(request: Request):
        """Serve the Model Browser admin interface. Unauthenticated users are redirected to /login."""
        if not _user_has_session(request):
            next_url = str(request.url)
            return RedirectResponse(url=f"/login?next={next_url}", status_code=302)
        return HTMLResponse(content=_admin_html)

    @app.get("/healthz")
    async def health_check():
        return {"status": "ok", "service": "pybpm-admin"}

    return app


app = create_app()


def main():
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = Config.PORT
    reload = Config.DEBUG
    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
