"""Unit & Integration tests for Register, Account Activation, Forgot Password, and Reset Password."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from integrity_checker.api.main import app
from integrity_checker.api.services.email_service import get_email_service
from integrity_checker.db.models import AuthToken, Session as SessionModel, User
from integrity_checker.db.repository import Repository
from integrity_checker.db.session import get_session


@pytest.fixture(autouse=True)
def clean_auth_db():
    """Ensure clean DB and email outbox before and after each test."""
    email_svc = get_email_service()
    email_svc.clear_outbox()
    session = get_session()
    session.query(AuthToken).delete()
    session.query(SessionModel).delete()
    session.query(User).delete()
    session.commit()
    session.close()
    yield
    email_svc.clear_outbox()
    session = get_session()
    session.query(AuthToken).delete()
    session.query(SessionModel).delete()
    session.query(User).delete()
    session.commit()
    session.close()


class TestRegisterAndActivateFlow:
    def test_register_creates_inactive_user_and_sends_html_email(self):
        client = TestClient(app)
        email_svc = get_email_service()

        resp = client.post(
            "/api/auth/register",
            json={
                "username": "student_minh",
                "email": "Minh.Student@example.com",
                "password": "StrongPassword123",
                "full_name": "Nguyễn Bảo Minh",
                "institution": "Ton Duc Thang University",
                "lang": "vi",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["username"] == "student_minh"
        assert data["email"] == "minh.student@example.com"
        assert data["requires_activation"] is True
        assert data["email_sent"] is True

        # Check HTML activation email in outbox
        assert len(email_svc.outbox) == 1
        sent = email_svc.outbox[0]
        assert sent.template_type == "activation"
        assert sent.to_email == "minh.student@example.com"
        assert sent.token is not None
        assert "Kích hoạt Tài khoản Ngay" in sent.html_body

        # Cannot log in before activating
        login_before = client.post(
            "/api/auth/login",
            json={"username": "student_minh", "password": "StrongPassword123"},
        )
        assert login_before.status_code == 403
        assert "ACCOUNT_NOT_ACTIVATED" in login_before.json()["detail"]

        # Activate account using token from email
        act_resp = client.post("/api/auth/activate", json={"token": sent.token})
        assert act_resp.status_code == 200, act_resp.text
        act_data = act_resp.json()
        assert act_data["activated"] is True
        assert act_data["already_active"] is False
        assert act_data["username"] == "student_minh"

        # Clicking the activation link a second time is idempotent when already active
        act_again = client.post("/api/auth/activate", json={"token": sent.token})
        assert act_again.status_code == 200
        assert act_again.json()["already_active"] is True

        # Can now log in by username AND by email
        login_after = client.post(
            "/api/auth/login",
            json={"username": "student_minh", "password": "StrongPassword123"},
        )
        assert login_after.status_code == 200
        assert login_after.json()["user"]["email_verified"] is True

        login_by_email = client.post(
            "/api/auth/login",
            json={"username": "minh.student@example.com", "password": "StrongPassword123"},
        )
        assert login_by_email.status_code == 200
        assert login_by_email.json()["user"]["username"] == "student_minh"

    def test_register_rejects_duplicate_username_or_email_or_bad_username(self):
        client = TestClient(app)

        # Invalid characters in username
        bad_user = client.post(
            "/api/auth/register",
            json={
                "username": "bad user space",
                "email": "a@example.com",
                "password": "password123",
            },
        )
        assert bad_user.status_code == 400

        # Valid registration
        ok = client.post(
            "/api/auth/register",
            json={
                "username": "scholar1",
                "email": "scholar1@example.com",
                "password": "password123",
            },
        )
        assert ok.status_code == 200

        # Duplicate username
        dup_u = client.post(
            "/api/auth/register",
            json={
                "username": "scholar1",
                "email": "other@example.com",
                "password": "password123",
            },
        )
        assert dup_u.status_code == 400
        assert "username" in dup_u.json()["detail"].lower()

        # Duplicate email (case-insensitive)
        dup_e = client.post(
            "/api/auth/register",
            json={
                "username": "scholar2",
                "email": "SCHOLAR1@EXAMPLE.COM",
                "password": "password123",
            },
        )
        assert dup_e.status_code == 400
        assert "email" in dup_e.json()["detail"].lower()

    def test_resend_activation_invalidates_old_token_and_issues_new(self):
        client = TestClient(app)
        email_svc = get_email_service()

        client.post(
            "/api/auth/register",
            json={
                "username": "resend_user",
                "email": "resend@example.com",
                "password": "password123",
            },
        )
        first_token = email_svc.outbox[-1].token
        assert first_token is not None

        # Resend activation using username
        resend_resp = client.post(
            "/api/auth/resend-activation",
            json={"identifier": "resend_user", "lang": "en"},
        )
        assert resend_resp.status_code == 200
        second_token = email_svc.outbox[-1].token
        assert second_token is not None
        assert second_token != first_token

        # Old token should now be rejected
        old_act = client.post("/api/auth/activate", json={"token": first_token})
        assert old_act.status_code == 400

        # New token activates the account
        new_act = client.post("/api/auth/activate", json={"token": second_token})
        assert new_act.status_code == 200
        assert new_act.json()["activated"] is True

        # Resending when already active returns 400
        already_resp = client.post(
            "/api/auth/resend-activation",
            json={"identifier": "resend@example.com"},
        )
        assert already_resp.status_code == 400

    def test_expired_or_invalid_activation_token_rejected(self):
        client = TestClient(app)
        email_svc = get_email_service()

        # Totally invalid token
        bad = client.post("/api/auth/activate", json={"token": "nonexistent_token"})
        assert bad.status_code == 400

        # Expired token
        client.post(
            "/api/auth/register",
            json={
                "username": "exp_user",
                "email": "exp@example.com",
                "password": "password123",
            },
        )
        tok = email_svc.outbox[-1].token
        assert tok is not None

        session = get_session()
        repo = Repository(session)
        row = repo.get_auth_token(tok, "activation")
        assert row is not None
        row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        session.commit()
        session.close()

        exp_resp = client.post("/api/auth/activate", json={"token": tok})
        assert exp_resp.status_code == 400
        assert "expired" in exp_resp.json()["detail"].lower()


class TestForgotPasswordAndResetFlow:
    def test_full_forgot_and_reset_password_flow_revokes_sessions(self):
        client = TestClient(app)
        email_svc = get_email_service()

        # Register & activate user
        client.post(
            "/api/auth/register",
            json={
                "username": "prof_lan",
                "email": "lan@example.com",
                "password": "OldPassword123",
                "full_name": "PGS.TS Nguyễn Thị Lan",
            },
        )
        act_tok = email_svc.outbox[-1].token
        client.post("/api/auth/activate", json={"token": act_tok})

        # Login to create an active JWT session
        login1 = client.post(
            "/api/auth/login",
            json={"username": "prof_lan", "password": "OldPassword123"},
        )
        assert login1.status_code == 200
        old_jwt = login1.json()["token"]

        # Request forgot password
        email_svc.clear_outbox()
        forgot_resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "lan@example.com", "lang": "vi"},
        )
        assert forgot_resp.status_code == 200
        assert len(email_svc.outbox) == 1
        reset_email = email_svc.outbox[0]
        assert reset_email.template_type == "password_reset"
        reset_token = reset_email.token
        assert reset_token is not None

        # Verify reset token endpoint
        verify_resp = client.get(f"/api/auth/verify-reset-token?token={reset_token}")
        assert verify_resp.status_code == 200
        vdata = verify_resp.json()
        assert vdata["valid"] is True
        assert vdata["username"] == "prof_lan"
        assert vdata["email"] == "lan@example.com"

        # Reset password
        reset_resp = client.post(
            "/api/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "NewSecurePassword456",
                "lang": "vi",
            },
        )
        assert reset_resp.status_code == 200

        # Password changed notification email sent
        assert email_svc.outbox[-1].template_type == "password_changed"

        # Token cannot be reused
        reuse_verify = client.get(f"/api/auth/verify-reset-token?token={reset_token}")
        assert reuse_verify.json()["valid"] is False
        assert reuse_verify.json()["reason"] == "used"

        reuse_reset = client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": "AnotherPassword789"},
        )
        assert reuse_reset.status_code == 400

        # Old JWT session should be revoked (401 on /api/auth/me)
        me_old = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {old_jwt}"},
        )
        assert me_old.status_code == 401

        # Old password no longer works
        old_login = client.post(
            "/api/auth/login",
            json={"username": "prof_lan", "password": "OldPassword123"},
        )
        assert old_login.status_code == 401

        # New password works
        new_login = client.post(
            "/api/auth/login",
            json={"username": "prof_lan", "password": "NewSecurePassword456"},
        )
        assert new_login.status_code == 200

    def test_forgot_password_unknown_email_does_not_leak_existence(self):
        client = TestClient(app)
        email_svc = get_email_service()

        resp = client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
        assert len(email_svc.outbox) == 0


class TestProductionSecurityGuards:
    def test_dev_latest_email_blocked_in_production_even_when_debug_true(self, monkeypatch):
        client = TestClient(app)
        email_svc = get_email_service()
        email_svc.send_activation_email(
            to_email="victim@example.com",
            username="victim",
            full_name="Victim",
            raw_token="secret_tok_999",
        )
        # In test mode, dev endpoint works
        dev_resp = client.get("/api/auth/dev/latest-email?email=victim@example.com")
        assert dev_resp.status_code == 200
        assert dev_resp.json()["token"] == "secret_tok_999"

        # In production mode (even if debug=True), endpoint must return 404
        monkeypatch.setenv("APP_ENV", "production")
        prod_resp = client.get("/api/auth/dev/latest-email?email=victim@example.com")
        assert prod_resp.status_code == 404

    def test_email_outbox_not_populated_in_production(self, monkeypatch):
        email_svc = get_email_service()
        email_svc.clear_outbox()
        monkeypatch.setenv("APP_ENV", "production")

        email_svc.send_activation_email(
            to_email="produser@example.com",
            username="produser",
            full_name="Prod User",
            raw_token="prod_tok_123",
        )
        assert len(email_svc.outbox) == 0

    def test_demo_users_disabled_in_production(self, monkeypatch):
        from integrity_checker.api.routes.auth import _is_demo_enabled

        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEMO_USERS_ENABLED", "true")
        assert _is_demo_enabled() is False

    def test_login_rate_limiter_blocks_brute_force(self, monkeypatch):
        from integrity_checker.api.routes.auth import _login_rate_limiter

        _login_rate_limiter.clear_all()
        monkeypatch.setattr(_login_rate_limiter, "enforce_in_tests", True)
        monkeypatch.setattr(_login_rate_limiter, "max_attempts", 3)

        client = TestClient(app)
        try:
            for _ in range(3):
                r = client.post(
                    "/api/auth/login",
                    json={"username": "brute_target", "password": "wrong"},
                )
                assert r.status_code == 401

            blocked = client.post(
                "/api/auth/login",
                json={"username": "brute_target", "password": "wrong"},
            )
            assert blocked.status_code == 429
            assert "too many" in blocked.json()["detail"].lower()
        finally:
            _login_rate_limiter.clear_all()


class TestGoogleOAuthFlow:
    def test_google_config_endpoint_reflects_client_id(self, monkeypatch):
        client = TestClient(app)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        r1 = client.get("/api/auth/google/config")
        assert r1.status_code == 200
        assert r1.json() == {"enabled": False, "client_id": None}

        unconfigured_login = client.post(
            "/api/auth/google",
            json={"access_token": "dummy_tok"},
        )
        assert unconfigured_login.status_code == 503
        assert "GOOGLE_NOT_CONFIGURED" in unconfigured_login.json()["detail"]

        monkeypatch.setenv("GOOGLE_CLIENT_ID", "12345-citra.apps.googleusercontent.com")
        r2 = client.get("/api/auth/google/config")
        assert r2.status_code == 200
        assert r2.json() == {
            "enabled": True,
            "client_id": "12345-citra.apps.googleusercontent.com",
        }

    def test_google_login_creates_new_user_and_returns_jwt(self, monkeypatch):
        client = TestClient(app)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "12345-citra.apps.googleusercontent.com")
        monkeypatch.setattr(
            "integrity_checker.api.routes.auth._verify_google_payload",
            lambda req, cid, csec: {
                "sub": "google-sub-998877",
                "email": "Minh.Scholar@tdtu.edu.vn",
                "email_verified": True,
                "name": "Nguyễn Bảo Minh",
                "picture": "https://lh3.googleusercontent.com/a/avatar123",
            },
        )

        resp = client.post(
            "/api/auth/google",
            json={"access_token": "valid_google_access_token"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["token"]
        user = data["user"]
        assert user["username"] == "minh.scholar"
        assert user["email"] == "minh.scholar@tdtu.edu.vn"
        assert user["full_name"] == "Nguyễn Bảo Minh"
        assert user["avatar_url"] == "https://lh3.googleusercontent.com/a/avatar123"
        assert user["auth_provider"] == "google"
        assert user["google_linked"] is True
        assert user["email_verified"] is True
        assert user["is_active"] is True

        # Verify session token works with /api/auth/me
        me_resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {data['token']}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "minh.scholar"

    def test_google_login_links_existing_unactivated_user_and_activates_account(
        self, monkeypatch
    ):
        client = TestClient(app)
        # Register local user (unactivated)
        reg = client.post(
            "/api/auth/register",
            json={
                "username": "custom_handle",
                "email": "linked@tdtu.edu.vn",
                "password": "LocalPassword123",
            },
        )
        assert reg.status_code == 200

        monkeypatch.setenv("GOOGLE_CLIENT_ID", "12345-citra.apps.googleusercontent.com")
        monkeypatch.setattr(
            "integrity_checker.api.routes.auth._verify_google_payload",
            lambda req, cid, csec: {
                "sub": "google-sub-linked-001",
                "email": "linked@tdtu.edu.vn",
                "email_verified": "true",
                "name": "Linked Scholar",
                "picture": "https://lh3.googleusercontent.com/a/linked",
            },
        )

        g_resp = client.post(
            "/api/auth/google",
            json={"credential": "valid_google_id_token"},
        )
        assert g_resp.status_code == 200, g_resp.text
        g_user = g_resp.json()["user"]
        # Preserves original username, activates account, and links Google
        assert g_user["username"] == "custom_handle"
        assert g_user["is_active"] is True
        assert g_user["email_verified"] is True
        assert g_user["google_linked"] is True
        assert g_user["auth_provider"] == "local,google"
        assert g_user["full_name"] == "Linked Scholar"

        # Original local password still works after Google account linking
        local_login = client.post(
            "/api/auth/login",
            json={"username": "custom_handle", "password": "LocalPassword123"},
        )
        assert local_login.status_code == 200

    def test_google_login_blocks_deactivated_user(self, monkeypatch):
        client = TestClient(app)
        session = get_session()
        repo = Repository(session)
        u = repo.create_user(
            username="deactivated_scholar",
            password_hash="hash",
            role="user",
            email="blocked@tdtu.edu.vn",
            is_active=False,
            email_verified=True,
        )
        session.commit()
        session.close()

        monkeypatch.setenv("GOOGLE_CLIENT_ID", "12345-citra.apps.googleusercontent.com")
        monkeypatch.setattr(
            "integrity_checker.api.routes.auth._verify_google_payload",
            lambda req, cid, csec: {
                "sub": "google-sub-blocked",
                "email": "blocked@tdtu.edu.vn",
                "email_verified": True,
                "name": "Blocked User",
            },
        )

        resp = client.post(
            "/api/auth/google",
            json={"access_token": "tok"},
        )
        assert resp.status_code == 403
        assert "ACCOUNT_DEACTIVATED" in resp.json()["detail"]

    def test_google_login_rejects_mismatched_google_id_on_existing_email(self, monkeypatch):
        client = TestClient(app)
        session = get_session()
        repo = Repository(session)
        repo.create_user(
            username="existing_google_user",
            password_hash="hash",
            role="user",
            email="conflict@tdtu.edu.vn",
            is_active=True,
            email_verified=True,
            google_id="original-google-sub-111",
            auth_provider="google",
        )
        session.commit()
        session.close()

        monkeypatch.setenv("GOOGLE_CLIENT_ID", "12345-citra.apps.googleusercontent.com")
        monkeypatch.setattr(
            "integrity_checker.api.routes.auth._verify_google_payload",
            lambda req, cid, csec: {
                "sub": "different-google-sub-222",
                "email": "conflict@tdtu.edu.vn",
                "email_verified": True,
                "name": "Conflict User",
            },
        )

        resp = client.post(
            "/api/auth/google",
            json={"access_token": "tok"},
        )
        assert resp.status_code == 403
        assert "linked to a different Google account" in resp.json()["detail"]

    def test_google_login_filters_non_https_avatar_and_rejects_unverified_email(
        self, monkeypatch
    ):
        client = TestClient(app)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "12345-citra.apps.googleusercontent.com")

        # Unverified Google email must be rejected
        monkeypatch.setattr(
            "integrity_checker.api.routes.auth._verify_google_payload",
            lambda req, cid, csec: {
                "sub": "google-sub-unverified",
                "email": "unverified@tdtu.edu.vn",
                "email_verified": False,
                "name": "Unverified",
            },
        )
        r_unverified = client.post(
            "/api/auth/google",
            json={"access_token": "tok"},
        )
        assert r_unverified.status_code == 403
        assert "not verified" in r_unverified.json()["detail"]

        # Non-https avatar URL must be ignored
        monkeypatch.setattr(
            "integrity_checker.api.routes.auth._verify_google_payload",
            lambda req, cid, csec: {
                "sub": "google-sub-http-avatar",
                "email": "httpavatar@tdtu.edu.vn",
                "email_verified": True,
                "name": "HTTP Avatar",
                "picture": "javascript:alert(1)",
            },
        )
        r_avatar = client.post(
            "/api/auth/google",
            json={"access_token": "tok"},
        )
        assert r_avatar.status_code == 200
        assert r_avatar.json()["user"]["avatar_url"] is None



