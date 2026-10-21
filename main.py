"""PyBPM Editor — FastAPI application entry point.

Serves:
- Static Oryx editor assets (JS/CSS/images) at /static
- Login page at /login
- Redirect from / to /login
- Logout that clears the stored token and returns to login
- The Model Browser UI at /admin (requires authentication — client-side guard)
- The Model Manager UI at /manager/model/{idwf} (requires authentication — client-side guard)
"""

import json
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


def _find_shape_by_id(child_shapes: list, resource_id: str) -> dict | None:
    """Recursively search childShapes for a shape matching resource_id."""
    for shape in child_shapes:
        if shape.get("resourceId") == resource_id:
            return shape
        children = shape.get("childShapes", [])
        if children:
            result = _find_shape_by_id(children, resource_id)
            if result:
                return result
    return None


async def _fetch_case_data(idwf: str, case_id: str) -> dict:
    """Fetch data object from pybpm-api case manager."""
    api_url = Config.PYBPM_API_URL.rstrip("/")
    url = f"{api_url}/bpm/case_manager/data/{idwf}/{case_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            return {"_error": f"pybpm-api returned {resp.status_code}: {resp.text}"}
    except (httpx.ConnectError, httpx.TimeoutException) as err:
        return {"_error": f"pybpm-api unreachable: {err}"}
    except Exception as err:
        return {"_error": f"Error fetching case data: {err}"}


class NoCacheMiddleware:
    """Add Cache-Control headers to prevent browser caching of admin pages."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            should_nocache = (
                path
                in (
                    "/admin",
                    "/",
                    "/login",
                    "/logout",
                    "/editor",
                    "/editor/code",
                    "/manager",
                    "/manager/model",
                    "/rbac",
                )
                or path.startswith("/static/jscript/")
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
            # Pass through pybpm-api's own status codes (401 for bad credentials)
            from fastapi import HTTPException

            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Authentication service error: {resp.text}",
            )
    except httpx.ConnectError as err:
        raise HTTPException(
            status_code=500,
            detail="Authentication service unavailable (backend database connection failed)",
        ) from err
    except httpx.TimeoutException as err:
        raise HTTPException(
            status_code=500,
            detail="Authentication service timed out",
        ) from err

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
        title="PyBPM Admin",
        version="0.1.0",
        openapi_url="/openapi.json",
    )

    templates = Jinja2Templates(directory=str(_base_dir / "templates"))
    # Make Jinja2 templates available in route handlers via request.app.state.templates.

    # CORS: allow pybpm-api origin (editor save/load) and same-origin admin calls.
    origins = [
        f"http://localhost:{Config.APP_PORT}",
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
        """Serve the standalone login page.

        Captures the intended post-login redirect target from:
        1. ?redirect= query parameter (set by client-side auth redirects)
        2. Referer header (browser back-navigation)
        Falls back to /admin if neither is available or referer is /logout.
        """
        # Prefer explicit ?redirect= parameter
        redirect = request.query_params.get("redirect")

        if not redirect:
            # Fallback to Referer header
            referer = request.headers.get("referer", "")
            if referer:
                # Extract path from full URL (e.g. "http://host/admin?foo=bar" → "/admin")
                from urllib.parse import urlparse

                parsed = urlparse(referer)
                redirect = parsed.path

        # Special case: if the user came from /logout, always redirect to /admin
        if redirect == "/logout":
            redirect = "/admin"

        # Default fallback
        if not redirect:
            redirect = "/admin"

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "Config": Config, "redirect": redirect},
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

    @app.get("/editor")
    async def editor_page(request: Request, idwf: str | None = None):
        """Render the Oryx-based BPMN model editor page.

        Serves the full ExtJS 2.0 + Oryx editor shell with all legacy JS/CSS assets.
        Optional ?idwf= query parameter loads an existing model by IDWF on startup.
        """
        return templates.TemplateResponse(
            request=request,
            name="editor.html",
            context={
                "request": request,
                "title": "Oryx Editor",
                "base_url": "/static/editor/",  # editor: oryx assets under static/editor/
                "module_url": f"{Config.ADMIN_URL_PREFIX}/",
                "apiUrl": f"{Config.PYBPM_API_URL}/",
                "idwf": idwf or "",
                "Config": Config,
            },
        )

    @app.get("/admin")
    async def admin_editor(request: Request):
        """Render the Model Browser UI. Authentication is enforced client-side via localStorage."""
        """Render the ext-ui editor page. Uses Newb() arrays from legacy Admin."""
        base_url = "static/"
        module_url = "browser/"

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
            f"{base_url}/{module_url}/ext.settings.js": "Settings",
            f"{base_url}/{module_url}/ext.model-utils.js": "Model Utils",
            f"{base_url}/{module_url}/data.js": "Data Objects",
            f"{base_url}/{module_url}/tree.js": "Module Tree",
            f"{base_url}/{module_url}/ext.add_events.js": "Events for overlays",
            f"{base_url}/{module_url}/center_panel.js": "Center Panel",
            f"{base_url}/{module_url}/viewport.js": "Viewport",
        }

        global_js = {
            "base_url": base_url,
            "module_url": module_url,
        }

        return templates.TemplateResponse(
            request=request,
            name="ext-ui.html",
            context={
                "request": request,
                "title": "Model Browser",
                "base_url": global_js["base_url"],
                "module_url": global_js["module_url"],
                "api_module": "/bpm/repository",
                "css": _render_css(css_dict),
                "js": _render_js(js_dict),
                "Config": Config,
            },
        )

    @app.get("/rbac")
    async def rbac_page(request: Request):
        """Render the RBAC Admin UI (groups, users, permissions)."""
        base_url = "static/"
        module_url = "rbac/"

        css_dict = {
            f"{base_url}jscript/ext/src/ux/css/CheckHeader.css": "checkHeader",
            f"{base_url}css/admin.css": "Admin css",
            f"{base_url}css/load_mask.css": "loadingmask",
        }

        js_dict = {
            f"{base_url}/{module_url}ext.settings.js": "Settings",
            f"{base_url}/{module_url}data.js": "Group Data Objects",
            f"{base_url}jscript/ext/src/ux/form/SearchField.js": "Search Field",
            f"{base_url}/{module_url}dataview.js": "Data View",
            f"{base_url}/{module_url}tree.js": "Perm Tree",
            f"{base_url}/{module_url}grid.js": "Users Grid",
            f"{base_url}/{module_url}userform.js": "Users Edit Form",
            f"{base_url}/{module_url}app.js": "Viewport",
        }

        return templates.TemplateResponse(
            request=request,
            name="rbac.html",
            context={
                "request": request,
                "title": "RBAC Admin",
                "base_url": base_url,
                "module_url": module_url,
                "api_url": Config.PYBPM_API_URL,
                "css": _render_css(css_dict),
                "js": _render_js(js_dict),
                "Config": Config,
            },
        )

    @app.get("/manager/model/{idwf}")
    async def manager_model(request: Request, idwf: str):
        """Render the Model Manager UI for a specific BPMN model.

        Serves the ExtJS-based model browser/editor shell with all assets under
        ``static/manager``. The ``idwf`` path segment identifies the loaded model.
        Authentication is enforced client-side via localStorage.
        """
        base_url = "../../static/"
        module_url = "manager/"

        css_dict = {
            f"{base_url}css/jsoneditor.min.css": "JSON Editor CSS",
            f"{base_url}css/case_manager.css": "Manager Styles",
            f"{base_url}css/extra-icons.css": "Extra Icons",
            f"{base_url}css/fix_bootstrap_checkbox.css": "Fix Checkbox",
        }

        js_dict = {
            f"{base_url}jscript/jquery/jquery.min.js": "JQuery",
            # ----Pan & ZooM---------------------------------------------
            f"{base_url}jscript/panzoom/jquery.panzoom.min.js": "Panzoom Minified",
            f"{base_url}jscript/panzoom/jquery.mousewheel.js": "wheel-suppport",
            f"{base_url}jscript/panzoom/pnazoom_wheel.js": "wheel script",
            # -----------------------------------------------------------------
            f"{base_url}jscript/jsoneditor.min.js": "JSON-Editor",
            f"{base_url}{module_url}ext.settings.js": "Settings & overrides",
            f"{base_url}jscript/fontawesome_icons.js": "FontAwesome icons",
            f"{base_url}{module_url}ext.data.js": "data Components",
            f"{base_url}jscript/ext/src/ux/form/SearchField.js": "Search Field",
            f"{base_url}{module_url}ext.tokenGrid.js": "Types Grid",
            f"{base_url}{module_url}ext.grid.js": "Grid",
            f"{base_url}{module_url}/ext.model-utils.js": "Model utils",
            f"{base_url}{module_url}ext.add_events.js": "Events for overlays",
            f"{base_url}{module_url}ext.viewport.js": "viewport",
            f"{base_url}jscript/bootstrap/js/bootstrap.min.js": "Bootstrap JS",
        }

        global_js = {
            "base_url": base_url,
            "module_url": module_url,
            "idwf": idwf,
        }
        return templates.TemplateResponse(
            request=request,
            name="ext-ui.html",
            context={
                "request": request,
                "title": "Model Manager",
                "base_url": base_url,
                "module_url": module_url,
                "api_module": "bpm/",
                "idwf": idwf,
                "css": _render_css(css_dict),
                "js": _render_js(js_dict),
                "Config": Config,
            },
        )

    @app.get("/healthz")
    async def health_check():
        return {"status": "ok", "service": "pybpm-admin"}

    # ---- Code Editor API endpoints ----

    @app.get("/code/{idwf}/{case_id}/{resource_id}")
    async def get_shape_code(idwf: str, case_id: str, resource_id: str):
        """Fetch script data for a shape in a model."""
        model_path = (
            Path(Config.STATIC_ROOT) / "files" / "images" / "model" / f"{idwf}.json"
        )
        if not model_path.is_file():
            return JSONResponse(
                status_code=404,
                content={"error": f"Model not found: {idwf}.json"},
            )
        try:
            model = json.loads(model_path.read_text())
        except json.JSONDecodeError as err:
            return JSONResponse(
                status_code=500,
                content={"error": f"Invalid model JSON: {err}"},
            )
        shape = _find_shape_by_id(model.get("childShapes", []), resource_id)
        if not shape:
            return JSONResponse(
                status_code=404,
                content={"error": f"Shape not found: {resource_id}"},
            )
        props = shape.get("properties", {})
        return JSONResponse(
            content={
                "resource_id": resource_id,
                "shape_name": props.get("name", ""),
                "script": props.get("script", ""),
                "script_language": props.get("script_language", ""),
                "operationref": props.get("operationref", ""),
            }
        )

    @app.get("/code/data/{idwf}/{case_id}")
    async def get_code_data(idwf: str, case_id: str):
        """Fetch the data object for a case from pybpm-api."""
        data = await _fetch_case_data(idwf, case_id)
        return JSONResponse(content=data)

    @app.post("/code/execute")
    async def execute_code(request: Request):
        """Execute a script via the morty sandbox API."""
        body = await request.json()
        language = body.get("language", "python")
        script = body.get("script", "")
        data = body.get("data", {})
        morty_url = Config.MORTY_API_URL.rstrip("/") + "/execute"
        payload = {"language": language, "script": script, "data": data}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(morty_url, json=payload)
                if resp.status_code == 200:
                    return JSONResponse(content=resp.json())
                return JSONResponse(
                    status_code=resp.status_code,
                    content={"error": resp.text},
                )
        except httpx.TimeoutException as err:
            return JSONResponse(
                status_code=504,
                content={"error": f"Morty timed out: {err}"},
            )
        except (httpx.ConnectError, httpx.NetworkError) as err:
            return JSONResponse(
                status_code=502,
                content={"error": f"Morty unreachable: {err}"},
            )

    @app.get("/editor/code/{idwf}/{case_id}/{resource_id}")
    async def code_editor_page(
        request: Request,
        idwf: str,
        case_id: str,
        resource_id: str,
    ):
        """Render the standalone code editor page."""
        return templates.TemplateResponse(
            request=request,
            name="code_editor.html",
            context={
                "request": request,
                "idwf": idwf,
                "case_id": case_id,
                "resource_id": resource_id,
            },
        )

    # Disable caching for admin/editor pages (ExtJS UI must always fetch fresh assets)

    return app


app = create_app()


def main():
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = Config.APP_PORT
    reload = Config.DEBUG
    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
