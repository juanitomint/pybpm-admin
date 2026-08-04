# Admin Interface — Migration Plan

## Overview

Port the legacy CodeIgniter `Admin` controller (`dna2bpm/application/modules/bpm/controllers/Admin.php`) into **pybpm-admin** as a standalone FastAPI project. The editor serves both an ExtJS-based Model Browser admin UI and HTML template views, using **pybpm-api** (port 5000) as the model persistence backend.

No URL-mapping proxy layer — pybpm-admin owns its own routes under `/admin/*` that translate legacy-style URLs into direct calls to pybpm-api's existing repository endpoints.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────────┐
│  pybpm-admin       │     │  pybpm-api               │
│  (FastAPI :8080)    │────▶│  /api/v1/bpm/repository/ │
│                     │     │                          │
│  /admin/*           │     │  GET  /load/model/{idwf} │
│   ├─ get_tree/json  │     │  POST /add/{idwf}        │
│   ├─ tree/{action}  │     │  POST /update_folder     │
│   ├─ import_form    │     │  DELETE /delete          │
│   └─ new_model_form │     │  POST /import            │
│                     │     │                          │
│  index.html         │     │  GET  /get_shapes/...    │
│  (Oryx editor)      │     │  GET  /svg/{idwf}        │
└─────────────────────┘     └──────────────────────────┘

Browser JS calls:
- Admin UI endpoints → pybpm-admin :8080 (own server, same origin)
- Oryx editor save/load → pybpm-api :5000 (?apiUrl=... query param)
```

**Key design decisions**:
- pybpm-admin is **independent of pybpm-api** — it's a self-contained FastAPI app, not a proxy.
- Admin endpoints (`/admin/*`) are defined directly in pybpm-admin's `admin_router.py`.
- The tree-building logic from legacy `convert_to_item` / `explodeTree` runs **inside pybpm-admin**, calling pybpm-api to fetch the raw model data, then transforming it locally.
- Form views (`import_form`, `new_model_form`) return JSON (not HTML), consumed by the ExtJS browser UI.

## Authentication

All admin endpoints require a JWT bearer token. The browser authenticates against **pybpm-api** (the identity provider) and carries the same token to both pybpm-admin and pybpm-api.

### Flow

```
Browser                          pybpm-api :5000              pybpm-admin :8080
   │                                  │                              │
   │  POST /api/v1/auth/token           │                              │
   │  {username, password}             │                              │
   │ ──────────────────────────────▶  │                              │
   │     {access_token, token_type}    │                              │
   │ ◀──────────────────────────────  │                              │
   │                                  │                              │
   │  GET /admin/get_tree/json         │                              │
   │  Authorization: Bearer <token>    │                              │
   │ ─────────────────────────────────┼────────────────────────────▶  │
   │                                  │     fetches models             │
   │                                  │ ◀── GET /load/model/{idwf}    │
   │                                  │     (with same Bearer token)   │
   │                                  │                              │
   │  {tree data}                     │                              │
   │ ◀────────────────────────────────┼────────────────────────────── │
```

1. **Login**: Browser calls `POST /api/v1/auth/token` with OAuth2 password form (`username`, `password`) on pybpm-api (port 5000). Returns `{access_token, token_type: "bearer"}`.
2. **Token storage**: Browser stores the JWT in `localStorage`. An auth shim (`auth_shim.js`) intercepts all `Ext.Ajax` and `Ext.data.Connection` requests to inject `Authorization: Bearer <token>`.
3. **Admin endpoints** (pybpm-admin :8080): Every `/admin/*` route validates the token by calling pybpm-api's `GET /api/v1/auth/me` with the bearer header. If valid, proceed; if 401, return 401 to browser. This avoids pybpm-admin having to decode/verify tokens itself — pybpm-api is the source of truth for identity.
4. **Backend calls** (pybpm-admin → pybpm-api): When pybpm-admin proxies requests to pybpm-api (e.g., fetching model data), it forwards the same bearer token from the browser's request. The backend call uses `httpx` with `Authorization: Bearer <token>` in headers.

### Token dependency

pybpm-api must be running and reachable for auth validation on every admin request. If pybpm-api is unavailable, admin endpoints return 503 (service unavailable) rather than granting access.

### Login UI

The ExtJS viewport loads a login panel before initializing the model browser tree. The user enters credentials into an ExtJS form; on submit, `auth_shim.js` POSTs to pybpm-api's token endpoint. On success, the token is stored and the main viewport renders with full admin access.

## Legacy-to-Backend Mapping

Each legacy Admin.php method maps to an endpoint in pybpm-admin that calls pybpm-api for persistence. **All endpoints require a valid JWT bearer token** (see Authentication section above):

| Legacy method | Route (pybpm-admin) | Backend call(s) to pybpm-api |
|---|---|---|
| `get_tree()` | GET `/admin/get_tree/json` | `GET /load/model/{idwf}` for each model, then `explodeTree` locally |
| `tree($action)` | POST/GET `/admin/tree/{action}` | Varies per action (see below) |
| `get_tree2()` | GET `/admin/get_tree2/json` | Same as get_tree + `convert_to_ext` locally |
| `import_form()` | GET `/admin/import_form` | Returns import UI config JSON |
| `new_model_form()` | GET `/admin/new_model_form` | Calls `GET /load/model/*` to collect unique folders |
| `get_data($idwf, $idcase)` | GET `/admin/get_data/{idwf}/{idcase}` | Requires BPM engine (deferred) |
| `get_model($idwf)` | GET `/admin/get_model/{idwf}?mode=json` | `GET /load/model/{idwf}` |
| `get_models()` | GET `/admin/get_models[?folder=&order=]` | `GET /load/model/{idwf}` for each, filter locally |
| `model_move($from, $to)` | POST `/admin/model_move` | `POST /update_folder` |

### Tree CRUD actions (`tree/$action`)

| Action | Backend call to pybpm-api | Purpose |
|--------|--------------------------|---------|
| `create` | `POST /add/{idwf}` + optional folder set via `POST /update_folder` | Create new model scaffold in a folder. Auth: `Authorization: Bearer <token>` forwarded to pybpm-api. |
| `read` | (same as get_tree) | Refresh tree from backend. Auth token validated by pybpm-admin before fetching models from pybpm-api. |
| `update` | `POST /update_folder` | Move model to different folder (`parentId`). Auth: same bearer token forwarded. |
| `destroy` | `DELETE /delete` | Remove model. Auth: same bearer token forwarded. |

## Backend Endpoints Used (pybpm-api)

These endpoints already exist in pybpm-api's `app/api/bpm/repository.py`. **All require `Authorization: Bearer <token>`** from the original browser request — pybpm-admin forwards the token when proxying calls to pybpm-api.

| Endpoint | Method | Purpose | Admin use case |
|---|---|---|---|
| `/load/model/{idwf}` | GET | Load full model JSON data | Tree building, get_model, new_model_form folder list |
| `/add/{idwf}` | POST | Create empty model scaffold | tree/create action |
| `/update_folder` | POST | Move model to different folder | tree/update, model_move |
| `/delete` | DELETE | Delete a model by idwf | tree/destroy action |
| `/import` | POST | Upload .zip with model JSON+SVG | import_form → user uploads → editor calls directly or via admin proxy |
| `/get_shapes/model/{idwf}` | GET | Walk shapes dict for toolbar/stencil panel | Oryx editor (not admin UI) |
| `/svg/{idwf}` | GET | Serve SVG file from disk | Oryx editor rendering |
| `/api/v1/auth/token` | POST | Login — returns JWT | Browser → pybpm-api identity provider |
| `/api/v1/auth/me` | GET | Validate token, return user info | pybpm-admin validates admin auth |

**Note**: `tree`, `tree2`, and `models` endpoints do **not** exist in pybpm-api. The tree-building logic (`explodeTree`, `convert_to_ext`) runs inside pybpm-admin using data fetched from `/load/model/{idwf}`. This keeps pybpm-admin self-contained for admin concerns.

## Step-by-Step Plan

### Phase 0 — Project structure in pybpm-admin

**Goal**: Set up the FastAPI project skeleton in pybpm-admin with config, router, and dependency management.

1. Add `config.py` to pybpm-admin (same pattern as pybpm-api: dotenv + class Config).
2. Create `pyproject.toml` with FastAPI, uvicorn, httpx, ruff dependencies.
3. Create `admin_router.py` — the main router mirroring Admin.php endpoints.
4. Update `main.py` (or create new entry point) to mount static files + admin router.
5. Add `.env` template and update `docker-compose.yml` for FastAPI instead of nginx.

**Deliverables**:
- [ ] `config.py` with env-driven settings (`PYBPM_API_URL`, etc.)
- [ ] `pyproject.toml` with `fastapi`, `uvicorn[standard]`, `httpx`, `ruff`
- [ ] `admin_router.py` — empty router scaffold with all route stubs from Admin.php
- [ ] Updated entry point (`main.py`) serving static files + admin routes on port 8080
- [ ] Updated `docker-compose.yml` using Python/uvicorn image instead of nginx

---

### Phase 1 — Tree endpoints (get_tree, get_tree2)

**Goal**: Implement the two tree-building endpoints that are core to the Model Browser.

The legacy code builds trees in two formats:
- **`get_tree()`** → nested JSON with `id`, `text`, `item[]` children, userdata (`idwf`, `ismodel`) for ExtJS TreePanel. Uses `explodeTree` to convert flat paths into hierarchical dict, then `convert_to_item` to format nodes.
- **`get_tree2()`** → ExtJS TreePanel-compatible tree with `leaf`, `cls: 'folder'/'user'`, `children[]`. Uses `explodeTree` + `convert_to_ext` (different variant that produces `leaf`/`iconCls` fields).

**Steps**:
1. Implement `explode_tree(paths_dict, delimiter='/')` — converts `{path: name}` dicts into nested `{folder: {subfolder: ...}}` structures. Pure function, no HTTP calls.
2. In `/admin/get_tree/json`: fetch all models from pybpm-api (`/load/model/{idwf}`), build a `{path: name}` dict using each model's folder/idwf/name, run `explode_tree`, then format with `convert_to_item`-style node structure returning `{root: {Home: [nodes]}}`.
3. In `/admin/get_tree2/json`: same flow but format with `convert_to_ext`-style (leaf/cls/iconCls).
4. Both endpoints need to handle the "folder" concept — models have a `data.properties.name` and a top-level `idwf` field from the DB model.

**Deliverables**:
- [ ] `explode_tree()` pure function with tests
- [ ] `/admin/get_tree/json` endpoint returning nested ExtJS tree JSON
- [ ] `/admin/get_tree2/json` endpoint returning leaf/children format
- [ ] Tests verifying tree shape matches legacy output for sample data

---

### Phase 2 — Tree CRUD actions + model operations

**Goal**: Wire admin routes to pybpm-api backend calls.

**Steps**:
1. `/admin/tree/create`: forward to `POST /add/{idwf}` on pybpm-api, then if a folder was specified in the request body, call `POST /update_folder` with the new idwf + folder.
2. `/admin/tree/update`: receive `{id: modelId, parentId: newFolder}`, call `POST /update_folder` on pybpm-api (`{idwf, folder}`).
3. `/admin/tree/destroy`: receive model idwf, call `DELETE /delete` on pybpm-api with body `{idwf}`.
4. `/admin/get_model/{idwf}`: proxy GET to `pybpm-api /load/model/{idwf}`, return response as-is (JSON mode) or wrap in template context (HTML mode).
5. `/admin/get_models[?folder=&order=]`: fetch all models from pybpm-api, filter by folder if provided, sort by name or version, return flat array with id/idwf/version/name/documentation fields.
6. `/admin/model_move/{from}/{to}`: call `POST /update_folder` on pybpm-api to move model between folders (note: legacy method signature is positional; we'll use a JSON body `{idwf, folder}`).

**Deliverables**:
- [ ] `/admin/tree/create` → pybpm-api POST /add + optional /update_folder
- [ ] `/admin/tree/update` → pybpm-api POST /update_folder
- [ ] `/admin/tree/destroy` → pybpm-api DELETE /delete
- [ ] `/admin/get_model/{idwf}` proxy to pybpm-api /load/model/{idwf}
- [ ] `/admin/get_models[?folder=&order=]` with filter + sort
- [ ] `/admin/model_move` POST endpoint
- [ ] httpx-based integration tests hitting a mock pybpm-api

---

### Phase 3 — Form views (import_form, new_model_form)

**Goal**: Replace PHP template rendering with JSON API responses consumed by ExtJS forms.

Legacy methods:
- `import_form()` → renders `bpm/import_form.php` template (HTML page with file upload form).
- `new_model_form()` → renders `bpm/new_model_form.php`, queries all models to build a folder dropdown list.

**Steps**:
1. `/admin/import_form`: return JSON config for the import UI — `{upload_url, accept: '.zip', help_text}`. The ExtJS browser's `center_panel.js` handles rendering the actual upload form client-side; this endpoint just provides metadata.
2. `/admin/new_model_form`: fetch all models from pybpm-api to extract unique folder values, return `{folders: ["General", "Subfolder1", ...]}` as JSON.

**Deliverables**:
- [ ] `/admin/import_form` → static JSON config response
- [ ] `/admin/new_model_form` → returns available folders list (fetched from pybpm-api)
- [ ] Tests for folder extraction logic

---

### Phase 4 — Browser JS integration and authentication

**Goal**: Wire the existing ExtJS browser code (`static/jscript/browser/`) to call admin endpoints on the same origin, and implement the login flow that authenticates against pybpm-api before the model browser initializes.

The browser UI files are served by FastAPI's `StaticFiles` mount at `/static`. The JavaScript uses `globals.apiUrl` to build API URLs:

```javascript
var apiUrl = (new URLSearchParams(window.location.search)).get('apiUrl') || '';
// admin endpoints live on same origin:
'/';                    // pybpm-admin root (serves index.html + static)
'/admin/';            // admin API prefix (same server)
// editor persistence calls go to pybpm-api:
if (apiUrl) {
  window.globals.apiUrl = apiUrl;             // e.g., http://localhost:5000/api/v1
}
```

**Steps**:
1. Update `index.html` bootstrap to set `globals.apiUrl = '/admin/'` and `globals.base_url = '/'`.
2. The existing browser JS files (`data.js`, `tree.js`, `viewport.js`) already build URLs like `globals.apiUrl + 'get_tree2/json'` — these now resolve to `/admin/get_tree2/json` which is served by pybpm-admin itself. No file changes needed in `static/`.
3. Add `auth_shim.js`: intercepts all `Ext.Ajax.request`, `Ext.data.Connection`, and `Ext.data.JsonStore` calls. If the request target starts with `/admin/` (pybpm-admin) or matches the globals.apiUrl prefix (pybpm-api), inject `Authorization: Bearer <token>` from localStorage.
4. Add login flow: before ExtJS viewport initializes, check if a valid JWT exists in localStorage. If not, show an ExtJS login panel with username/password fields. On submit, POST `{username, password}` to pybpm-api's `/api/v1/auth/token`. Store the returned token in localStorage.
5. Add token refresh/revalidation: periodically call `GET /api/v1/auth/me` on pybpm-api to verify the token is still valid. If it returns 401, clear the token and show the login panel again.

**Deliverables**:
- [ ] `index.html`: globals set to `/admin/` for module_url, root for base_url
- [ ] `auth_shim.js` (new): intercepts Ext.Ajax, injects Bearer token from localStorage
- [ ] Login form component: ExtJS panel with username/password → POST to pybpm-api /token
- [ ] Browser JS verified: tree.js/data.js URLs resolve correctly to own server
- [ ] Manual E2E: open editor → login screen appears → enter credentials → tree loads from `/admin/get_tree/json`

---

### Phase 5 — Docker + CORS configuration

**Goal**: Ensure pybpm-admin (port 8080) and pybpm-api (port 5000) work together in Docker Compose.

**Steps**:
1. Update `docker-compose.yml` so editor uses a Python image with uvicorn instead of nginx.
2. Verify CORS settings in pybpm-api allow `localhost:8080` origin for Oryx editor save/load calls (pybpm-api already has wildcard CORS, should be fine).
3. Test full flow end-to-end with Docker Compose: admin tree loads from editor's own server, model save goes to pybpm-api on port 5000.

**Deliverables**:
- [ ] Updated `docker-compose.yml` with FastAPI service for editor
- [ ] CORS verified between ports 8080 ↔ 5000
- [ ] Docker Compose E2E working

---

### Phase 6 — Out-of-scope items (future)

The following legacy Admin methods are **not** ported in this initial pass:

| Legacy method | Reason | Future owner |
|--------------|--------|-------------|
| `movi()` | Deprecated UI (`/5`), redirects to case manager | pybpm-ui React |
| `get_data($idwf, $idcase)` | Requires BPM engine (case token data) | Engine module in pybpm-api |
| Group/User CRUD from `data.js` | RBAC is separate concern | RBAC service in pybpm-api |
| KPI/Status/Manager toolbar buttons | Require engine + case manager | pybpm-ui / engine |
| Model export as .zip download | Requires zip packaging logic | repository.py extension or editor UI |

---

## Testing Strategy

1. **Unit tests** (pybpm-admin): Test `explode_tree()` with various folder structures — deep nesting, flat lists, single items. Verify output shape matches legacy `convert_to_item` / `convert_to_ext`.
2. **Integration tests**: Spin up a mock pybpm-api, hit admin endpoints, verify correct backend calls are made and responses match expected shapes. Include auth validation tests (valid token → 200, missing token → 401, expired/invalid token → 401).
3. **Auth flow tests**: Mock pybpm-api's `/auth/token` and `/auth/me`, verify that admin endpoints reject requests without a valid bearer token and accept requests with one.
4. **Config override tests**: Change `PYBPM_API_URL` env var, verify admin router resolves to the new backend URL.
5. **Manual E2E**: Open editor at `localhost:8080/?apiUrl=http://localhost:5000/api/v1`, enter credentials in login panel → tree loads from `/admin/get_tree/json`, browse models, save via pybpm-api with authenticated requests.

## Progress Tracking

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Project structure in pybpm-admin | ⬜ Not started | config.py, admin_router.py scaffold, FastAPI setup, auth dependency on pybpm-api |
| 1 — Tree endpoints (get_tree, get_tree2) | ⬜ Not started | explodeTree + convert_to_item/convert_to_ext logic |
| 2 — Tree CRUD + model operations | ⬜ Not started | Wire to pybpm-api backend calls with auth forwarding |
| 3 — Form views (import_form, new_model_form) | ⬜ Not started | JSON responses replacing PHP templates |
| 4 — Browser JS integration + login flow | ⬜ Not started | auth_shim.js, login panel, globals set in index.html |
| 5 — Docker + CORS configuration | ⬜ Not started | FastAPI container instead of nginx, both services running |
| 6 — Out-of-scope items | ⬜ Deferred | Engine/RBAC/ui modules |
