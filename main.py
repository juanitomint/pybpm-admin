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
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.types import ASGIApp, Receive, Scope, Send

from config import Config


class NoCacheMiddleware:
    """Add Cache-Control headers to prevent browser caching of admin pages."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            should_nocache = path in (
                "/admin",
                "/admin2",
                "/",
                "/login",
                "/logout",
            ) or path.startswith("/static/jscript/")

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


async def _authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user via pybpm-api /auth/token endpoint."""
    auth_url = Config.PYBPM_API_URL.rstrip("/") + "/api/v1/auth/token"
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


def _render_css(css_dict):
    lines = []
    for url, desc in css_dict.items():
        lines.append(f"<!-- CSS:{desc} -->")
        lines.append(f"<link rel='stylesheet' type='text/css' href='{url}' />")
    return "\n".join(lines)


def _render_js(js_dict):
    lines = []
    for url, desc in js_dict.items():
        lines.append(f"<!-- JS:{desc} -->")
        lines.append(
            f"""<script type="text/javascript">
try{{document.getElementById('loading-msg').innerHTML +="<span class='ok'>OK.</span><br/>Loading {desc}...";}}catch(e){{}}</script>"""
        )
        lines.append(f"<script type='text/javascript' src='{url}'></script>")
    return "\n".join(lines)


def create_app() -> FastAPI:
    app = FastAPI(
        title="PyBPM Editor",
        version="0.1.0",
        openapi_url="/openapi.json",
    )

    templates = Jinja2Templates(directory=str(_base_dir / "templates"))
    # Make Jinja2 templates available in route handlers via request.app.state.templates.

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

    @app.get("/login")
    async def login_page(request: Request):
        """Serve the standalone login page."""
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "Config": Config},
        )

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

    @app.get("/logout")
    async def logout(request: Request):
        """Clear bpm_token from localStorage and redirect to /login."""
        return templates.TemplateResponse(
            request=request,
            name="logout.html",
            context={"request": request},
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/admin")
    async def admin_editor(request: Request):
        """Render the Model Browser UI. Authentication is enforced client-side via localStorage."""
        """Render the ext-ui editor page. Uses Newb() arrays from legacy Admin."""
        css_dict, js_dict, global_js = newb()

        return templates.TemplateResponse(
            request=request,
            name="ext-ui.html",
            context={
                "request": request,
                "title": "Model Browser",
                "base_url": global_js["base_url"],
                "module_url": global_js["module_url"],
                "css": _render_css(css_dict),
                "js": _render_js(js_dict),
                "Config": Config,
            },
        )

    def newb():
        """Replicate the legacy Admin::Newb() JS/CSS/global_js arrays.

        Migrated from dna2bpm/application/modules/bpm/controllers/Admin.php::Newb().
        Returns the same data structure that was previously passed to
        $this->ui->makeui('ext.ui-no-ion.php', $cpData).
        """
        base_url = "static/"
        module_url = f"{Config.ADMIN_URL_PREFIX}/"

        css_dict = {
            f"{base_url}/jscript/ext/src/ux/css/CheckHeader.css": "checkHeader",
            f"{base_url}/css/load_mask.css": "loadingmask",
            f"{base_url}/css/browser.css": "Browser",
            f"{base_url}/css/extra-icons.css": "Extra Icons",
        }

        js_dict = {
            f"{base_url}jscript/jquery/jquery.min.js": "JQuery",
            # ----Pan & ZooM---------------------------------------------
            f"{base_url}/jscript/panzoom/jquery.panzoom.min.js": "Panzoom Minified",
            f"{base_url}/jscript/panzoom/jquery.mousewheel.js": "wheel-suppport",
            f"{base_url}/jscript/panzoom/pnazoom_wheel.js": "wheel script",
            # -----------------------------------------------------------------
            f"{base_url}/jscript/ext.settings.js": "Settings",
            f"{base_url}/jscript/browser/ext.model-utils.js": "Model Utils",
            f"{base_url}/jscript/browser/data.js": "Data Objects",
            f"{base_url}/jscript/browser/tree.js": "Module Tree",
            f"{base_url}/jscript/browser/ext.add_events.js": "Events for overlays",
            f"{base_url}/jscript/browser/center_panel.js": "Center Panel",
            f"{base_url}/jscript/browser/viewport.js": "Viewport",
        }

        global_js = {
            "base_url": base_url,
            "module_url": module_url,
        }

        return css_dict, js_dict, global_js

    @app.get("/healthz")
    async def health_check():
        return {"status": "ok", "service": "pybpm-admin"}

    # Disable caching for admin/editor pages (ExtJS UI must always fetch fresh assets)

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
