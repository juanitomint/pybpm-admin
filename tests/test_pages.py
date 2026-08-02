"""Integration tests — HTML page serving (/, /admin, /login)."""


class TestIndexPage:
    """Tests for the editor index page served at GET /.

    Serves the Oryx BPMN model editor shell page.
    """

    def test_index_returns_200(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/")
        assert resp.status_code == 200

    def test_index_serves_html_content_type(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_index_contains_api_url_config(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get("/").text
        assert "apiUrl" in body
        assert "editor_api" in body

    def test_index_contains_browser_scripts(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get("/").text
        assert "loadBrowserScripts" in body
        assert "browser/data.js" in body
        assert "browser/tree.js" in body
        assert "browser/viewport.js" in body


class TestAdminPage:
    """Tests for the Model Browser admin page served at GET /admin.

    Unauthenticated requests are redirected to /login. Authenticated requests
    (with bpm_session cookie) serve the full ExtJS-based browser UI.
    """

    def test_admin_redirects_unauthenticated(self, sync_test_client):  # type: ignore[no-untyped-def]
        """Unauthenticated /admin redirects to /login with the original URL."""
        resp = sync_test_client.get("/admin", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_admin_includes_next_url_in_redirect(self, sync_test_client):  # type: ignore[no-untyped-def]
        """The redirect preserves the original URL via ?next= so the user returns here after login."""
        resp = sync_test_client.get(
            "/admin?apiUrl=http://localhost:5000/api/v1",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "next=" in location

    def test_admin_serves_with_valid_session(self, sync_test_client):  # type: ignore[no-untyped-def]
        """With a valid session cookie, /admin serves the Model Browser UI."""
        resp = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        )
        assert resp.status_code == 200

    def test_admin_serves_html_content_type(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        )
        assert "text/html" in resp.headers["content-type"]

    def test_admin_contains_loading_mask(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "loading-mask" in body

    def test_admin_loads_extjs_framework(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "ext-all.js" in body

    def test_admin_loads_jquery_and_panzoom(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "jquery.min.js" in body
        assert "panzoom" in body

    def test_admin_loads_browser_js_stack(self, sync_test_client):  # type: ignore[no-untyped-def]
        """Full browser UI JS stack loaded in order (data → tree → center → viewport)."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "browser/data.js" in body
        assert "browser/tree.js" in body
        assert "browser/center_panel.js" in body
        assert "browser/ext.add_events.js" in body
        assert "browser/viewport.js" in body

    def test_admin_loads_auth_shim(self, sync_test_client):  # type: ignore[no-untyped-def]
        """auth_shim.js must load before browser JS to inject Bearer tokens."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "auth_shim.js" in body

    def test_auth_shim_loaded_before_data_js(self, sync_test_client):  # type: ignore[no-untyped-def]
        """auth_shim must appear earlier in HTML than data.js (injection order)."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        shim_pos = body.index("auth_shim.js")
        data_pos = body.index("browser/data.js")
        assert shim_pos < data_pos

    def test_admin_loads_ext_settings_and_model_utils(self, sync_test_client):  # type: ignore[no-untyped-def]
        """ExtJS configuration and model utilities loaded before browser scripts."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "ext.settings.js" in body
        assert "ext.model-utils.js" in body

    def test_admin_sets_module_url_to_admin_prefix(self, sync_test_client):  # type: ignore[no-untyped-def]
        """globals.module_url must be /admin/ so browser JS calls admin endpoints."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "module_url" in body
        assert "/admin/" in body

    def test_admin_passes_apiurl_query_param(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get(
            "/admin?apiUrl=http://localhost:5000/api/v1",
            headers={"Cookie": "bpm_session=mock-token"},
        )
        assert resp.status_code == 200
        body = resp.text
        assert "apiUrl" in body

    def test_admin_loads_browser_css(self, sync_test_client):  # type: ignore[no-untyped-def]
        """Browser UI stylesheets loaded (browser.css, load_mask, extra-icons)."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "browser.css" in body
        assert "load_mask.css" in body
        assert "extra-icons.css" in body

    def test_admin_has_editor_container(self, sync_test_client):  # type: ignore[no-untyped-def]
        """ExtJS Viewport renders into this container (west=center layout)."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "editor-container" in body

    def test_admin_no_inline_login_overlay(self, sync_test_client):  # type: ignore[no-untyped-def]
        """The standalone /login page handles auth — no inline overlay on /admin."""
        body = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-token"},
        ).text
        assert "login-overlay" not in body


class TestLoginPage:
    """Tests for the standalone login page at GET /login."""

    def test_login_returns_200(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/login")
        assert resp.status_code == 200

    def test_login_serves_html_content_type(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/login")
        assert "text/html" in resp.headers["content-type"]

    def test_login_contains_form_action(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get("/login").text
        assert 'action="/login"' in body

    def test_login_contains_username_field(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get("/login").text
        assert 'name="username"' in body

    def test_login_contains_password_field(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get("/login").text
        assert 'name="password"' in body


class TestHealthCheck:
    """Tests for the /healthz endpoint."""

    def test_healthz_returns_200(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/healthz")
        assert resp.status_code == 200

    def test_healthz_json_body(self, sync_test_client):  # type: ignore[no-untyped-def]
        data = sync_test_client.get("/healthz").json()
        assert data["status"] == "ok"
        assert data["service"] == "pybpm-admin"
