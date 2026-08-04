"""PyBPM Editor — FastAPI application entry point.

Serves:
- Static Oryx editor assets (JS/CSS/images) at /static
- Login page at /login
- Redirect from / to /login
- Logout that clears the stored token and returns to login
- The Model Browser UI at /admin (requires authentication — client-side guard)
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from config import Config


class NoCacheMiddleware:
    """Add Cache-Control headers to prevent browser caching of admin pages."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            should_nocache = (
                path in ("/admin", "/", "/login", "/logout") or path.startswith("/static/jscript/")
            )

            if not should_nocache:
                await self.app(scope, receive, send)
                return

            original_send = send

            async def modified_send(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers[b"cache-control"] = b"no-cache, no-store, must-revalidate"
                    headers[b"pragma"] = b"no-cache"
                    headers[b"expires"] = b"0"
                    message["headers"] = list(headers.items())
                await original_send(message)

            await self.app(scope, receive, modified_send)
        else:
            await self.app(scope, receive, send)


_base_dir = Path(__file__).resolve().parent
_login_html = (_base_dir / "login.html").read_text(encoding="utf-8")
_admin_html = (_base_dir / "admin.html").read_text(encoding="utf-8")

# HTML returned by /logout to clear bpm_token from localStorage and redirect.
_LOGOUT_HTML = """\
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>DNA2BPM — Signing out</title></head>
<body>
<script>window.localStorage.removeItem("bpm_token"); window.location.href = "/login";</script>
<noscript>You are being <a href="/login">redirected to the sign-in page</a>.</noscript>
</body>
</html>\
"""


async def _authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user via pybpm-api /auth/token endpoint."""
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

    # CORS: allow pybpm-api origin (editor save/load) and same-origin admin calls.
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

    @app.get("/", response_class=RedirectResponse)
    async def root_redirect():
        """Redirect / to /login so users always land on the sign-in page."""
        return RedirectResponse(url="/login", status_code=302)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        """Serve the standalone login page."""
        return HTMLResponse(content=_login_html)

    @app.post("/login")
    async def login_submit(
        username: str = Form(...),
        password: str = Form(...),
    ):
        """Validate credentials via pybpm-api and return the access_token as JSON."""
        auth_data = await _authenticate_user(username, password)

        if auth_data is None or "access_token" not in auth_data:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid username or password"},
            )

        return JSONResponse(content={"access_token": auth_data["access_token"]})

    @app.get("/logout", response_class=HTMLResponse)
    async def logout():
        """Clear bpm_token from localStorage and redirect to /login."""
        return HTMLResponse(
            content=_LOGOUT_HTML,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/admin")
    async def admin_editor(request: Request):
        """Render the Model Browser UI. Authentication is enforced client-side via localStorage."""
        return HTMLResponse(content=_admin_html)

    @app.get("/healthz")
    async def health_check():
        return {"status": "ok", "service": "pybpm-admin"}

    # Disable caching for admin/editor pages (ExtJS UI must always fetch fresh assets)
    app = NoCacheMiddleware(app)

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
