# AGENTS.md — pybpm-admin/

## Purpose

FastAPI project that serves the **Model Browser admin interface** (porting `Admin.php` from legacy DNA2BPM) alongside the Oryx-based BPMN model editor. Replaces the previous nginx static-serve approach with a Python backend providing both API endpoints and HTML templates for the admin UI.

## Tech Stack

- **Framework**: FastAPI (synchronous + async mixed)
- **Static file serving**: `starlette.staticfiles.StaticFiles` (replaces nginx)
- **Server**: uvicorn
- **Editor engine**: Oryx (existing JS/CSS/images from legacy codebase, served unchanged)
- **Package Manager**: `uv`

## Architecture

```
pybpm-admin/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration class — reads env vars (same pattern as pybpm-api)
├── admin_router.py         # Admin API endpoints — mirrors legacy Admin.php controllers
│                           # Routes: /admin/get_tree, /admin/tree/create, etc.
├── index.html              # Editor shell page — loads existing Oryx libraries
├── templates/              # Jinja2 HTML templates rendered by admin endpoints
│   └── *.html              # Form views (import_form, new_model_form, etc.)
├── static/                 # Exact copy of legacy Oryx assets (read-only from dna2bpm)
│   ├── css/                # Editor stylesheets (browser.css, dna2.css, etc.)
│   ├── images/             # Icons, SVGs, loaders
│   ├── jscript/            # ExtJS, Oryx libs, model-utils, tokens, manual_task
│   └── types/              # Type definitions used by editor JS
└── .gitignore

pybpm-api/  ← separate repo; pybpm-admin is independent and self-contained.
```

**Key design decision**: pybpm-admin is an **independent FastAPI service** (not a proxy into pybpm-api). It owns the admin interface endpoints (`/admin/*`) that the ExtJS browser UI calls directly. The Oryx editor communicates with pybpm-api for model persistence; pybpm-admin handles the Model Browser / admin CRUD layer.

## Legacy Mapping: Admin.php → FastAPI Router

The `Admin` controller in legacy PHP maps to `admin_router.py`:

| Legacy method | Route pattern (pybpm-admin) | Purpose |
|---|---|---|
| `Index()` / `Newb()` | GET `/` | Model Browser UI — serves index.html with ExtJS viewport |
| `get_tree()` | GET `/admin/get_tree/json` | Nested JSON tree of models for ExtJS TreePanel |
| `tree($action)` | POST/GET `/admin/tree/{action}` | CRUD on model folders (create, read, update, destroy) |
| `get_tree2()` | GET `/admin/get_tree2/json` | ExtJS-compatible flat tree with leaf/children format |
| `import_form()` | GET `/admin/import_form` | Import model form view / JSON data |
| `new_model_form()` | GET `/admin/new_model_form` | New model form with available folders list |
| `get_data($idwf, $idcase)` | GET `/admin/get_data/{idwf}/{idcase}` | Case data for a given model (requires engine) |
| `get_model($idwf, $mode)` | GET `/admin/get_model/{idwf}[?mode=json]` | Single model representation (JSON or HTML) |
| `get_models()` | GET `/admin/get_models[?folder=&order=]` | Flat list of all models with filter/sort |
| `model_move($from, $to)` | POST `/admin/model_move` | Move a model between folders |

Internal helpers (`convert_to_item`, `convert_to_ext`, `explodeTree`) are reused as pure functions inside the router — no separate endpoints.

## Connecting to pybpm-api (Model Persistence)

The Oryx editor communicates with `pybpm-api` for model save/load. The API base URL is set via the `PYBPM_API_URL` environment variable (loaded from `.env`), which `index.html` reads at serve time and exposes as a JS global (`globals.apiUrl`) for the editor JavaScript to use:

```
.env → PYBPM_API_URL=http://localhost:5000/api/v1
index.html bootstrap → window.globals.apiUrl = 'http://localhost:5000/api/v1'
Oryx editor JS → fetch(globals.apiUrl + '/bpm/repository/svg/{idwf}')
```

| Method | Endpoint on pybpm-api | Purpose |
|--------|----------------------|---------|
| GET | `/bpm/repository/svg/{idwf}` | Load model SVG for rendering
| PUT | `/bpm/repository/save/{idwf}` | Save edited model back to API
| POST | `/auth/token` | Authenticate user before editing
| GET | `/bpm/repository/get_shapes/model/{idwf}` | Shape metadata for toolbar/stencil panel

The admin interface (ExtJS browser UI) calls pybpm-admin's own `/admin/*` endpoints — not pybpm-api directly.

## Development Workflow

### Local (without Docker)

```bash
# Install dependencies:
uv sync

# Set PYBPM_API_URL in .env (e.g., http://localhost:5000/api/v1)
uv run uvicorn main:app --reload --port 8080

# Then visit: http://localhost:8080/
```

### With Docker

```bash
docker compose up -d admin
# Then visit: http://localhost:8080/
```

## Linting & Formatting

After making any code changes, always run:

```bash
uv run ruff check --fix .
uv run ruff format .
```

Ruff enforces style rules. Configured in `pyproject.toml`.

## Git & Commits

All git operations run from within `pybpm-admin/` — never in the parent workspace folder.

Use **Conventional Commits** with **Semantic Versioning**. The `.githooks/commit-msg` hook enforces formatting.

### Commit format
```
<type>(optional scope): <description>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

### Examples
- `feat(admin): add model browser tree endpoint`
- `fix(editor): correct static asset path for panzoom`
- `refactor(admin): extract explodeTree into pure utility function`

## Important Notes

- **Do not modify** the contents of `static/`. It is an exact copy from legacy and must stay unchanged.
- The Oryx editor code was written for ExtJS 4.x and older browser APIs. It will run as-is in modern browsers — no transpilation or bundling needed.
- pybpm-admin is **independent of pybpm-api** — it does not proxy requests to it. It mounts pybpm-api's static SVGs only if they exist on disk, but admin endpoints are self-contained.
- Configuration follows the same pattern as pybpm-api: `config.py` imports dotenv and exposes a `Config` class with class-level attributes matching env var names. Other modules read via `Config.<ATTRIBUTE>`.
- If new features are added to the editor shell, they go into `index.html` without touching the `static/` directory.
