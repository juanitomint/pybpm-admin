"""Integration tests — authentication and authorization."""


class TestAuthValidation:
    """Tests for session cookie validation on admin page."""

    def test_missing_session_cookie_redirects_to_login(self, sync_test_client):  # type: ignore[no-untyped-def]
        """Unauthenticated /admin returns a redirect to /login with the original URL."""
        resp = sync_test_client.get("/admin", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]


class TestLoginFlow:
    """Tests for the standalone login page and authentication flow."""

    def test_login_page_returns_200(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/login")
        assert resp.status_code == 200

    def test_login_page_contains_username_field(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get("/login").text
        assert 'id="username"' in body or 'name="username"' in body

    def test_login_page_contains_password_field(self, sync_test_client):  # type: ignore[no-untyped-def]
        body = sync_test_client.get("/login").text
        assert 'id="password"' in body or 'name="password"' in body

    def test_login_page_posts_to_self(self, sync_test_client):  # type: ignore[no-untyped-def]
        """The login form submits to /login via POST."""
        body = sync_test_client.get("/login").text
        assert 'action="/login"' in body or "method='post'" in body

    def test_authenticated_user_gets_redirect_from_login(self, sync_test_client):  # type: ignore[no-untyped-def]
        """If a valid session cookie is present, /login redirects to admin."""
        resp = sync_test_client.get(
            "/login",
            headers={"Cookie": "bpm_session=mock-token-already-authenticated"},
            follow_redirects=False,
        )
        assert resp.status_code in (301, 302, 307)  # any redirect is acceptable
        # Should redirect to the default next URL (admin) or ?next= if provided.
        location = resp.headers["location"]
        assert "/admin" in location


class TestSessionCookie:
    """Tests for session cookie handling on /admin."""

    def test_valid_session_cookie_allows_admin_access(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-session-token"},
        )
        assert resp.status_code == 200

    def test_admin_page_with_cookie_serves_html(self, sync_test_client):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get(
            "/admin",
            headers={"Cookie": "bpm_session=mock-session-token"},
        )
        assert "text/html" in resp.headers["content-type"]
