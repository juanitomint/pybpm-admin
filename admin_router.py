"""FastAPI router for the Model Browser admin interface.

Mirrors legacy CodeIgniter `Admin` controller:
  dna2bpm/application/modules/bpm/controllers/Admin.php

All endpoints under `/admin/*`. Each one calls pybpm-api (port 5000) as the
backend for model persistence — see ADMIN.md for full mapping.
"""

from __future__ import annotations

from urllib.parse import unquote_plus

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from config import Config

router = APIRouter(prefix=Config.ADMIN_URL_PREFIX, tags=["admin"])


# -- Auth helpers ------------------------------------------------------------ #

SESSION_COOKIE_NAME = "bpm_session"


def _extract_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header or session cookie.

    Production browsers send the JWT via auth_shim.js reading bpm_session cookie.
    Tests may pass it either as a Bearer header or via Cookie header — accept both.
    """
    # 1) Try Authorization: Bearer <token> first (legacy / direct API access).
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]

    # 2) Fall back to session cookie bpm_session.
    cookie_header = request.headers.get("cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(SESSION_COOKIE_NAME + "="):
            return part[len(SESSION_COOKIE_NAME) + 1 :]

    return None


async def get_current_user(request: Request) -> dict:
    """Validate the bearer token by calling pybpm-api's /auth/me endpoint.

    Returns user dict on success. Raises 401 if no/invalid token,
    or 503 if pybpm-api is unreachable.
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    auth_url = Config.PYBPM_API_URL.rstrip("/") + "/auth/me"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(auth_url, headers=headers, timeout=5.0)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth service returned {resp.status_code}",
        )

    return resp.json()


async def _call_backend(
    request: Request, method: str, path: str, **kwargs
) -> dict | list:
    """Make an authenticated call to pybpm-api backend.

    Forwards the Authorization header from the original browser request so
    pybpm-api's auth middleware sees the same user identity.
    """
    token = _extract_token(request)
    headers = {**kwargs.pop("headers", {})}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = Config.PYBPM_API_URL.rstrip("/") + path

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(method, url, headers=headers, **kwargs)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend service unavailable",
        )

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed on backend",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = {"detail": resp.text}
        raise HTTPException(
            status_code=resp.status_code,
            detail=body.get("detail", f"Backend returned {resp.status_code}"),
        )

    return resp.json()


# -- explodeTree utility (ported from legacy Admin.php) --------------------- #


def _explode_tree(array: dict[str, str], delimiter: str = "/") -> dict | bool:
    """Convert a flat `{path: name}` dict into a nested tree structure.

    Ported from legacy `Admin::explodeTree($array, $delimiter='/')`.
    Example input:  {"General/flow1": "My Flow", "HR/onboarding": "Onboarding"}
    Returns nested dict with asort applied at each level.
    """
    if not isinstance(array, dict):
        return False

    return_arr: dict = {}

    for key in sorted(array.keys()):
        val = array[key]
        parts = [p for p in key.split(delimiter) if p]
        leaf_part = parts.pop()

        parent_ref = return_arr
        for part in parts:
            if part not in parent_ref or not isinstance(parent_ref[part], dict):
                parent_ref[part] = {}
            parent_ref = parent_ref[part]

        if leaf_part not in parent_ref:
            parent_ref[leaf_part] = val

    def _sort(d):  # type: ignore[misc]
        if isinstance(d, dict):
            return {k: _sort(v) for k, v in sorted(d.items())}
        return d

    return _sort(return_arr)


# -- convert_to_item (ported from legacy Admin.php) ------------------------- #


def _convert_to_item(array, id_start: int = 1):
    """Convert nested tree dict to ExtJS TreePanel item format.

    Ported from legacy `Admin::convert_to_item($array, $id)`.
    Produces nodes with: id, text, child count, im0 (icon), and recursive item[].
    """
    rtn_arr = []
    counter = [id_start]

    def _next_id():  # type: ignore[misc]
        val = counter[0]
        counter[0] += 1
        return val

    for key, value in array.items():
        if isinstance(value, dict):
            sorted_value = {k: value[k] for k in sorted(value.keys())}
            rtn_arr.append(
                {
                    "id": str(_next_id()),
                    "text": key,
                    "child": len(sorted_value),
                    "im0": "folderClosed.gif",
                    "item": _convert_to_item(sorted_value, counter[0]),
                }
            )
            counter[0] += 1
        else:
            rtn_arr.append(
                {
                    "id": str(key),
                    "text": f"{value} ({key})",
                    "userdata": [
                        {"name": "idwf", "content": key},
                        {"name": "ismodel", "content": True},
                    ],
                }
            )

    return rtn_arr


# -- convert_to_ext (ported from legacy Admin.php) -------------------------- #


def _convert_to_ext(array):
    """Convert nested tree dict to ExtJS TreePanel format with leaf/cls fields.

    Ported from legacy `Admin::convert_to_ext($array)`.
    Produces nodes with: id, text, leaf bool, cls (folder/user), iconCls, children[].
    """
    rtn_arr = []

    for key, value in array.items():
        if isinstance(value, dict):
            sorted_value = {k: value[k] for k in sorted(value.keys())}
            children_flat = _convert_to_ext(sorted_value)
            # Flatten nested lists from recursive calls
            children = []
            for c in children_flat:
                if isinstance(c, list):
                    children.extend(c)
                else:
                    children.append(c)
            rtn_arr.append(
                {
                    "text": key,
                    "leaf": False,
                    "cls": "folder",
                    "expanded": True,
                    "children": children,
                }
            )
        else:
            rtn_arr.append(
                {
                    "id": str(key),
                    "text": value,
                    "leaf": True,
                    "iconCls": None,
                }
            )

    return rtn_arr


# -- Admin endpoints (mirror legacy Admin.php) -------------------------------- #


@router.get("/get_tree/json")
async def get_tree(request: Request):
    """Build a nested model tree for ExtJS TreePanel.

    Fetches all models from pybpm-api, builds {path: name} dict, runs
    explodeTree + convert_to_item to produce the legacy-compatible format.
    Requires auth — validates via pybpm-api /auth/me before proceeding.
    """
    await get_current_user(request)

    raw_models = await _call_backend(request, "GET", "/repository/get_models")
    if not isinstance(raw_models, list):
        raw_models = []

    path_name_map: dict[str, str] = {}
    for m in raw_models:
        folder = m.get("folder", "General") or "General"
        idwf = m.get("idwf", "")
        name = m.get("name", f"Model {idwf}")
        path = f"{folder}/{idwf}"
        path_name_map[path] = name

    tree_data = _explode_tree(path_name_map)
    item_tree = _convert_to_item(tree_data, 1)

    return JSONResponse(
        content={
            "id": 0,
            "item": [{"id": 1, "text": "Home", "item": item_tree}],
        }
    )


@router.post("/tree/create")
async def tree_create(body: dict = {}, request: Request = None):  # type: ignore[assignment]
    """Create a new model scaffold in the specified folder.

    Forwards to pybpm-api POST /repository/add/{idwf}, then optionally moves
    it into the requested folder via POST /repository/update_folder.
    """
    if request is None:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    await get_current_user(request)

    idwf = body.get("idwf", "")
    folder = body.get("folder", "General")

    if not idwf:
        raise HTTPException(status_code=400, detail="idwf is required")

    result = await _call_backend(
        request,
        "POST",
        f"/repository/add/{idwf}",
        json={},
    )

    if isinstance(result, dict) and not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("msg", "Failed to create model"),
        )

    # Move to folder if non-default
    if folder and folder != "General":
        await _call_backend(
            request,
            "POST",
            "/repository/update_folder",
            json={"idwf": idwf, "folder": folder},
        )

    return JSONResponse(content={"ok": True})


@router.get("/tree/read")
async def tree_read(request: Request):
    """Refresh/re-read the model tree from backend."""
    return await get_tree(request=request)


@router.post("/tree/update")
async def tree_update(body: dict | list = {}, request: Request = None):  # type: ignore[assignment]
    """Update folder assignment for one or more models.

    Accepts single object or array of {id, parentId} — parentId is the new folder name.
    Forwards to pybpm-api POST /repository/update_folder.
    """
    if request is None:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    await get_current_user(request)

    inputs = body if isinstance(body, list) else [body]
    results = []

    for wf in inputs:
        model_idwf = wf.get("id", "")
        new_folder = wf.get("parentId", "")
        if not model_idwf or not new_folder:
            continue
        result = await _call_backend(
            request,
            "POST",
            "/repository/update_folder",
            json={"idwf": model_idwf, "folder": new_folder},
        )
        results.append(result)

    return JSONResponse(content={"ok": True})


@router.post("/tree/destroy")
async def tree_destroy(body: dict = {}, request: Request = None):  # type: ignore[assignment]
    """Delete a model. Forwards to pybpm-api DELETE /repository/delete."""
    if request is None:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    await get_current_user(request)

    idwf = body.get("id", "") or body.get("idwf", "")
    if not idwf:
        raise HTTPException(status_code=400, detail="idwf is required")

    result = await _call_backend(
        request,
        "DELETE",
        "/repository/delete",
        json={"idwf": idwf},
    )

    return JSONResponse(content=result)


@router.get("/get_tree2/json")
async def get_tree2(request: Request):
    """Proxy to pybpm-api /repository/get_tree2/json.

    The actual tree-building logic lives on the backend (see repository.py).
    This endpoint just forwards the authenticated call and returns whatever
    JSON the backend produces.
    """
    await get_current_user(request)
    return await _call_backend(request, "GET", "/repository/get_tree2/json")


@router.get("/get_models")
async def get_models(
    folder: str | None = Query(None),
    order: str = Query("data.properties.name"),
    request: Request = None,  # type: ignore[assignment]
):
    """Return flat list of all models with optional folder filter and sort."""
    if request is None:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    await get_current_user(request)

    raw_models = await _call_backend(request, "GET", "/repository/get_models")
    if not isinstance(raw_models, list):
        raw_models = []

    if folder:
        raw_models = [m for m in raw_models if m.get("folder") == folder]

    if raw_models and order.startswith("data.properties."):
        sort_key = order.replace("data.properties.", "")
        raw_models = sorted(raw_models, key=lambda m: m.get(sort_key, ""))

    return JSONResponse(content=raw_models)


@router.get("/get_model/{idwf}")
async def get_model(idwf: str, mode: str = "json", request: Request = None):  # type: ignore[assignment]
    """Return full model data for a given idwf.

    In JSON mode returns raw data; in HTML mode wraps with template context (deferred).
    """
    if request is None:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    await get_current_user(request)

    decoded_idwf = unquote_plus(idwf)
    model_data = await _call_backend(
        request,
        "GET",
        f"/repository/load/model/{decoded_idwf}",
    )

    if mode == "html":
        return JSONResponse(content={**model_data, "_mode": "html", "_base_url": "/"})

    return JSONResponse(content=model_data)


@router.get("/import_form")
async def import_form(request: Request):
    """Return import form configuration for the ExtJS upload panel."""
    await get_current_user(request)

    return JSONResponse(
        content={
            "upload_url": "/admin/import",
            "accept": ".zip",
            "help_text": "Upload a .zip archive containing {model_idwf}.json and {model_idwf}.svg",
        }
    )


@router.get("/new_model_form")
async def new_model_form(request: Request):
    """Return available folders list for the 'New Model' form dropdown."""
    await get_current_user(request)

    raw_models = await _call_backend(request, "GET", "/repository/get_models")
    if not isinstance(raw_models, list):
        raw_models = []

    folder_set: dict[str, int] = {}
    for m in raw_models:
        f = (m.get("folder") or "General").strip()
        folder_set[f] = 1
    if "General" not in folder_set:
        folder_set["General"] = 1

    folders = [{"folder": k} for k in sorted(folder_set.keys())]
    return JSONResponse(content={"folders": folders})


@router.post("/model_move")
async def model_move(body: dict = {}, request: Request = None):  # type: ignore[assignment]
    """Move a model from one folder to another.

    Accepts {idwf, folder} or {idwf, to}. Forwards to pybpm-api POST /repository/update_folder.
    """
    if request is None:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    await get_current_user(request)

    idwf = body.get("idwf", "")
    new_folder = body.get("folder") or body.get("to", "")

    if not idwf or not new_folder:
        raise HTTPException(status_code=400, detail="idwf and folder are required")

    result = await _call_backend(
        request,
        "POST",
        "/repository/update_folder",
        json={"idwf": idwf, "folder": new_folder},
    )

    return JSONResponse(content=result)


# -- Browser JS proxy endpoints (mirror legacy Admin.php routing) ------------ #


@router.post("/repository/add/{idwf}")
async def repository_add(idwf: str, request: Request):
    """Proxy for browser JS ModelAdd action — create model scaffold in a folder.

    Accepts form-encoded params {idwf, folder}, forwards to pybpm-api POST /add/{idwf}
    with the same bearer token. If a non-default folder is specified, also calls
    POST /update_folder to place it there.
    """
    await get_current_user(request)

    body = await request.form() if hasattr(request, "form") else {}
    # Also try JSON body for async clients
    try:
        json_body = await request.json()
        body = {**body, **json_body}
    except Exception:
        pass

    folder = body.get("folder", "General") or "General"

    result = await _call_backend(
        request,
        "POST",
        f"/add/{idwf}",
        json={"folder": folder},
    )

    if isinstance(result, dict) and not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("msg", "Failed to create model"),
        )

    # Move into specified folder (non-default) via pybpm-api update_folder
    if folder and str(folder).strip() != "General":
        await _call_backend(
            request,
            "POST",
            "/update_folder",
            json={"idwf": idwf, "folder": folder},
        )

    return JSONResponse(content=result)


@router.post("/repository/duplicate")
async def repository_duplicate(request: Request):
    """Proxy for browser JS ModelDuplicate action — clone a model to a new idwf."""
    await get_current_user(request)

    body = {}
    try:
        json_body = await request.json()
        body = json_body
    except Exception:
        pass

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body required")

    idwf = body.get("idwf", "")
    new_idwf = body.get("newidwf", "")

    if not idwf or not new_idwf:
        raise HTTPException(
            status_code=400, detail="Both 'idwf' and 'newidwf' are required"
        )

    result = await _call_backend(
        request,
        "POST",
        "/duplicate",
        json={"idwf": idwf, "new_idwf": new_idwf},
    )

    return JSONResponse(content=result)


@router.post("/repository/delete/model")
async def repository_delete_model(request: Request):
    """Proxy for browser JS ModelRemove action — delete a model by idwf."""
    await get_current_user(request)

    body = {}
    try:
        json_body = await request.json()
        body = json_body
    except Exception:
        pass

    # Also accept form-encoded params (legacy Ext.Ajax with params:)
    if not body:
        raw = await request.body()
        import urllib.parse as _uq

        parsed = _uq.parse_qs(raw.decode())
        for k, v in parsed.items():
            body[k] = v[0]

    idwf = body.get("idwf", "") or body.get("id", "")
    if not idwf:
        raise HTTPException(status_code=400, detail="idwf is required")

    result = await _call_backend(
        request,
        "DELETE",
        "/delete",
        json={"idwf": idwf},
    )

    return JSONResponse(content=result)


@router.post("/repository/update_folder")
async def repository_update_folder(request: Request):
    """Proxy for browser JS move_node action — move model between folders.

    Accepts form-encoded or JSON body {idwf, folder}. Forwards to pybpm-api
    POST /update_folder with auth token forwarding.
    """
    await get_current_user(request)

    body = {}
    try:
        json_body = await request.json()
        body = json_body
    except Exception:
        pass

    # Also accept form-encoded params (legacy Ext.Ajax with params:)
    if not body:
        raw = await request.body()
        import urllib.parse as _uq

        parsed = _uq.parse_qs(raw.decode())
        for k, v in parsed.items():
            body[k] = v[0]

    idwf = body.get("idwf", "") or body.get("id", "")
    folder = body.get("folder", "") or body.get("parentId", "")

    if not idwf or not folder:
        raise HTTPException(
            status_code=400, detail="Both 'idwf' and 'folder' are required"
        )

    result = await _call_backend(
        request,
        "POST",
        "/update_folder",
        json={"idwf": idwf, "folder": folder},
    )

    return JSONResponse(content=result)


@router.post("/repository/import/model")
async def repository_import_model(request: Request):
    """Proxy for browser JS ModelImport action — upload .zip model archive.

    Forwards multipart file upload to pybpm-api POST /import with auth token.
    """
    await get_current_user(request)

    # Extract Authorization header from the original request and forward it
    token = _extract_token(request) or ""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = Config.PYBPM_API_URL.rstrip("/") + "/import"

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, files={"file": request}, headers=headers)

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed on backend",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = {"detail": resp.text}
        raise HTTPException(
            status_code=resp.status_code,
            detail=body.get("detail", f"Backend returned {resp.status_code}"),
        )

    return JSONResponse(content=resp.json(), status_code=resp.status_code)


# -- Deferred: get_data (requires BPM engine) -------------------------------- #


@router.get("/get_data/{idwf}/{idcase}")
async def get_data(idwf: str, idcase: str, request: Request):
    """Return case data for a model/case pair. Requires BPM engine integration (deferred)."""
    await get_current_user(request)

    return JSONResponse(
        content={
            "idwf": idwf,
            "idcase": idcase,
            "data": {},
            "msg": "engine integration required",
        }
    )
