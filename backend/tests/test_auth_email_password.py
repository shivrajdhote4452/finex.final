"""Comprehensive automated tests for secure email-and-password authentication,
single-use verification/reset tokens, rate-limiting, and Google account linking.

Task: Secure email-and-password authentication alongside Google OAuth.
Ensures unified access to user data across both auth providers, preventing
account takeover vulnerabilities (OWASP compliance).
"""

import uuid
from unittest.mock import patch

import pytest
from backend.app.factory import create_app
from backend.app.services.email_service import email_service
from backend.app.services.password_service import auth_rate_limiter
from httpx import ASGITransport, AsyncClient

app = create_app()


@pytest.fixture(autouse=True)
def clean_rate_limiter_and_emails():
    """Reset rate limiter and email buffer before each test."""
    from backend.app.core.middleware import RateLimiterMiddleware

    email_service.enable_test_mode()
    RateLimiterMiddleware.reset_all()
    auth_rate_limiter.clear()
    email_service.clear_sent_emails()
    yield
    RateLimiterMiddleware.reset_all()
    auth_rate_limiter.clear()
    email_service.clear_sent_emails()
    email_service.enable_test_mode()


@pytest.mark.asyncio
async def test_signup_success_and_email_dispatched():
    """Test user signup with email, password, and name."""
    test_email = f"signup_{uuid.uuid4().hex[:8]}@example.com"
    signup_payload = {
        "email": test_email,
        "password": "SecurePassword123!",
        "name": "FinEx Test Investor",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["created"] is True
        assert body["data"]["email"] == test_email.lower()

        # Verify email was dispatched
        sent = email_service.get_last_email_for(test_email)
        assert sent is not None
        assert "token" in sent["metadata"]
        raw_token = sent["metadata"]["token"]
        assert len(raw_token) > 20


@pytest.mark.asyncio
async def test_signup_weak_password_fails():
    """Test that weak passwords below 8 characters or missing required character types fail validation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Too short
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "short@example.com", "password": "abc", "name": "Short"},
        )
        assert resp.status_code == 400
        assert "at least 8 characters" in resp.json()["detail"]

        # Only letters
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "nonum@example.com", "password": "onlyletterspassword", "name": "NoNum"},
        )
        assert resp.status_code == 400
        assert "number or special character" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_signup_duplicate_email_fails():
    """Test that duplicate signup returns HTTP 409 Conflict."""
    test_email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": test_email,
        "password": "Password123!",
        "name": "First Investor",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.post("/api/v1/auth/signup", json=payload)
        assert resp1.status_code == 200

        resp2 = await client.post("/api/v1/auth/signup", json=payload)
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_email_verification_success_and_consume():
    """Test email verification token validation and single-use enforcement."""
    test_email = f"verify_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": test_email, "password": "Password123!", "name": "To Verify"},
        )
        sent = email_service.get_last_email_for(test_email)
        token = sent["metadata"]["token"]

        # 1. Verify email
        resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert resp.status_code == 200
        assert resp.json()["data"]["verified"] is True

        # 2. Try using the exact same token again -> must fail (single-use)
        resp2 = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert resp2.status_code == 400
        assert "previously used" in resp2.json()["detail"].lower() or "invalid" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_unverified_email_fails():
    """Test that an unverified account cannot log in until verified."""
    test_email = f"unverified_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": test_email, "password": "Password123!", "name": "Unverified"},
        )

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "Password123!"},
        )
        assert resp.status_code == 403
        assert "not verified" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success_and_jwt_claims():
    """Test successful email and password login returns standard JWT access token."""
    test_email = f"loginsuccess_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Signup & verify
        await client.post(
            "/api/v1/auth/signup",
            json={"email": test_email, "password": password, "name": "Successful User"},
        )
        sent = email_service.get_last_email_for(test_email)
        token = sent["metadata"]["token"]
        await client.post("/api/v1/auth/verify-email", json={"token": token})

        # 2. Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": password},
        )
        assert login_resp.status_code == 200
        data = login_resp.json()["data"]
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["email"] == test_email.lower()
        jwt_token = data["access_token"]

        # 3. Access protected /users/me endpoint
        me_resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {jwt_token}"})
        assert me_resp.status_code == 200
        me_data = me_resp.json()["data"]
        assert me_data["email"] == test_email.lower()
        assert me_data["has_password"] is True
        assert me_data["email_verified"] is True


@pytest.mark.asyncio
async def test_login_wrong_password_fails():
    """Test that wrong password fails with generic 401 Unauthorized."""
    test_email = f"wrongpw_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": test_email, "password": password, "name": "Wrong Pass Tester"},
        )
        sent = email_service.get_last_email_for(test_email)
        await client.post("/api/v1/auth/verify-email", json={"token": sent["metadata"]["token"]})

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "WrongPassword999!"},
        )
        assert resp.status_code == 401
        assert "invalid email or password" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_rate_limiting():
    """Test that 5 consecutive failed login attempts trigger HTTP 429 Too Many Requests."""
    test_email = f"bruteforce_{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(5):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": test_email, "password": "WrongPassword!"},
            )
            assert resp.status_code in [401, 429]

        # 6th attempt must be blocked by rate limiter
        blocked_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "AnyPassword!"},
        )
        assert blocked_resp.status_code == 429
        assert "too many failed login attempts" in blocked_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_forgot_password_and_reset_flow():
    """Test full forgot-password and reset-password flow with single-use token."""
    test_email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Signup and verify
        await client.post(
            "/api/v1/auth/signup",
            json={"email": test_email, "password": old_password, "name": "Reset Tester"},
        )
        sent = email_service.get_last_email_for(test_email)
        await client.post("/api/v1/auth/verify-email", json={"token": sent["metadata"]["token"]})
        email_service.clear_sent_emails()

        # 1. Request password reset
        forgot_resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_email},
        )
        assert forgot_resp.status_code == 200
        assert forgot_resp.json()["data"]["sent"] is True

        reset_email = email_service.get_last_email_for(test_email)
        assert reset_email is not None
        reset_token = reset_email["metadata"]["token"]

        # 2. Reset password with valid token
        reset_resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": new_password},
        )
        assert reset_resp.status_code == 200
        assert reset_resp.json()["data"]["reset"] is True

        # 3. Old password should no longer work
        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": old_password},
        )
        assert old_login.status_code == 401

        # 4. New password works
        new_login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": new_password},
        )
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()["data"]

        # 5. Token cannot be reused
        reuse_resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": "AnotherPassword789!"},
        )
        assert reuse_resp.status_code == 400


@pytest.mark.asyncio
async def test_set_password_for_authenticated_google_user():
    """Test that a user signed in via Google can add an account password and subsequently log in via either method."""
    test_email = f"googleuser_{uuid.uuid4().hex[:8]}@gmail.com"
    google_sub = f"sub-google-{uuid.uuid4().hex[:10]}"

    fake_id_info = {
        "iss": "accounts.google.com",
        "sub": google_sub,
        "email": test_email,
        "email_verified": True,
        "name": "Google User",
    }

    with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_id_info):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Sign in via Google
            g_resp = await client.post("/api/v1/auth/google", json={"id_token": "valid-mock-token"})
            assert g_resp.status_code == 200
            google_jwt = g_resp.json()["data"]["access_token"]
            user_id = g_resp.json()["data"]["user_id"]

            # 2. Call /auth/set-password while authenticated
            set_pw_resp = await client.post(
                "/api/v1/auth/set-password",
                json={"new_password": "AddedPassword123!"},
                headers={"Authorization": f"Bearer {google_jwt}"},
            )
            assert set_pw_resp.status_code == 200
            assert set_pw_resp.json()["data"]["success"] is True

            # 3. User can now sign in using email & password
            pw_login_resp = await client.post(
                "/api/v1/auth/login",
                json={"email": test_email, "password": "AddedPassword123!"},
            )
            assert pw_login_resp.status_code == 200
            assert pw_login_resp.json()["data"]["access_token"] is not None
            assert pw_login_resp.json()["data"]["user_id"] == user_id


@pytest.mark.asyncio
async def test_account_linking_same_verified_email_shares_data():
    """Test that creating an account via email+password and later signing in with Google leads to the exact same user account, virtual cash, and holdings."""
    shared_email = f"shared_{uuid.uuid4().hex[:8]}@example.com"
    password = "MyPassword123!"
    google_sub = f"sub-shared-{uuid.uuid4().hex[:10]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register with email + password and verify email
        await client.post(
            "/api/v1/auth/signup",
            json={"email": shared_email, "password": password, "name": "Shared Account Owner"},
        )
        sent = email_service.get_last_email_for(shared_email)
        await client.post("/api/v1/auth/verify-email", json={"token": sent["metadata"]["token"]})

        # 2. Login via password
        pw_login = await client.post("/api/v1/auth/login", json={"email": shared_email, "password": password})
        assert pw_login.status_code == 200
        original_user_id = pw_login.json()["data"]["user_id"]
        pw_token = pw_login.json()["data"]["access_token"]

        # 3. Check initial paper account balance via password session
        acct_pw_resp = await client.get(
            "/api/v1/paper-trading/account", headers={"Authorization": f"Bearer {pw_token}"}
        )
        assert acct_pw_resp.status_code == 200
        cash_balance_pw = acct_pw_resp.json()["data"]["current_cash"]
        assert float(cash_balance_pw) == 100000.00

        # 4. Now sign in with Google using the same verified email
        fake_id_info = {
            "iss": "accounts.google.com",
            "sub": google_sub,
            "email": shared_email,
            "email_verified": True,
            "name": "Shared Account Owner",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_id_info):
            g_login = await client.post("/api/v1/auth/google", json={"id_token": "valid-mock-token"})
            assert g_login.status_code == 200
            google_user_id = g_login.json()["data"]["user_id"]
            google_token = g_login.json()["data"]["access_token"]

            # Must resolve to the EXACT SAME user_id!
            assert google_user_id == original_user_id

            # 5. Check paper account balance via Google session -> identical balance & account
            acct_g_resp = await client.get(
                "/api/v1/paper-trading/account", headers={"Authorization": f"Bearer {google_token}"}
            )
            assert acct_g_resp.status_code == 200
            cash_balance_g = acct_g_resp.json()["data"]["current_cash"]
            assert cash_balance_g == cash_balance_pw


@pytest.mark.asyncio
async def test_unverified_email_signup_pre_account_takeover_protection():
    """OWASP Mitigation: If an attacker signs up with victim@example.com (unverified),
    and the real owner authenticates with Google (verified), the unverified password
    must be invalidated so the attacker cannot log into the real owner's account.
    """
    victim_email = f"victim_{uuid.uuid4().hex[:8]}@example.com"
    attacker_password = "AttackerPassword123!"
    victim_google_sub = f"sub-victim-{uuid.uuid4().hex[:10]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Attacker signs up with victim's email but never verifies
        await client.post(
            "/api/v1/auth/signup",
            json={"email": victim_email, "password": attacker_password, "name": "Attacker"},
        )

        # 2. Real owner logs in with Google (verified email)
        fake_id_info = {
            "iss": "accounts.google.com",
            "sub": victim_google_sub,
            "email": victim_email,
            "email_verified": True,
            "name": "Real Victim",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_id_info):
            g_resp = await client.post("/api/v1/auth/google", json={"id_token": "valid-google-token"})
            assert g_resp.status_code == 200

        # 3. Attacker tries to log in with the unverified password -> MUST FAIL
        attacker_login = await client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": attacker_password},
        )
        assert attacker_login.status_code == 401


@pytest.mark.asyncio
async def test_google_unverified_email_refuses_auto_link():
    """Security: If a Google token has email_verified=False, it must NEVER auto-link
    to an existing user with that email.
    """
    existing_email = f"legit_{uuid.uuid4().hex[:8]}@example.com"
    existing_password = "LegitPassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Existing verified user
        s_res = await client.post(
            "/api/v1/auth/signup",
            json={"email": existing_email, "password": existing_password, "name": "Legit User"},
        )
        assert s_res.status_code == 200
        sent = email_service.get_last_email_for(existing_email)
        assert sent is not None
        v_res = await client.post("/api/v1/auth/verify-email", json={"token": sent["metadata"]["token"]})
        assert v_res.status_code == 200

        pw_login = await client.post(
            "/api/v1/auth/login",
            json={"email": existing_email, "password": existing_password},
        )
        assert pw_login.status_code == 200, f"pw_login failed: {pw_login.status_code} {pw_login.text}"
        legit_user_id = pw_login.json()["data"]["user_id"]

        # 2. Someone attempts Google login with an unverified email token
        fake_unverified_id_info = {
            "iss": "accounts.google.com",
            "sub": f"sub-fake-{uuid.uuid4().hex[:8]}",
            "email": existing_email,
            "email_verified": False,
            "name": "Impostor",
        }
        with patch(
            "backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_unverified_id_info
        ):
            g_resp = await client.post("/api/v1/auth/google", json={"id_token": "mock-unverified-token"})
            assert g_resp.status_code == 200
            # Must NOT be linked to legit_user_id!
            assert g_resp.json()["data"]["user_id"] != legit_user_id


@pytest.mark.asyncio
async def test_email_privacy_and_production_buffer_isolation():
    """Security: Ensure tokens, action links, and bodies are never stored in inspection buffer when not in test mode."""
    target_email = f"privacy_{uuid.uuid4().hex[:8]}@example.com"

    # 1. Disable test mode
    email_service.disable_test_mode()
    try:
        assert email_service.sent_emails == []
        assert email_service.get_last_email_for(target_email) is None

        # Direct service call without SMTP in production mode
        res = await email_service.send_verification_email(
            to_email=target_email,
            name="Privacy Tester",
            raw_token="sensitive-token-must-not-be-buffered",
        )
        assert res["status"] == "smtp_not_configured"
        assert res["delivered"] is False
        assert email_service.sent_emails == []
        assert email_service.get_last_email_for(target_email) is None

        # HTTP signup endpoint without test mode
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/signup",
                json={"email": target_email, "password": "SecurePassword123!", "name": "Privacy User"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["delivery_status"] == "smtp_not_configured"
            assert "unavailable" in data["message"].lower()
            # Buffer remains completely empty
            assert email_service.sent_emails == []
    finally:
        email_service.enable_test_mode()


@pytest.mark.asyncio
async def test_pre_account_takeover_invalidates_all_tokens_and_locks_attacker_out():
    """Security: When a verified Google owner claims an unverified account:
    1. The unverified password must be cleared.
    2. ALL pending verification and password-reset tokens must be immediately invalidated.
    3. The attacker cannot login, cannot verify with the old token, and cannot reset with the old token.
    """
    victim_email = f"victim_full_{uuid.uuid4().hex[:8]}@example.com"
    attacker_pw = "AttackerPw123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Attacker signs up with victim's email
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={"email": victim_email, "password": attacker_pw, "name": "Attacker Name"},
        )
        assert signup_res.status_code == 200
        signup_mail = email_service.get_last_email_for(victim_email)
        assert signup_mail is not None
        attacker_verify_token = signup_mail["token"]

        # 2. Attacker also requests a password reset token before owner logs in
        forgot_res = await client.post("/api/v1/auth/forgot-password", json={"email": victim_email})
        assert forgot_res.status_code == 200
        reset_mail = email_service.get_last_email_for(victim_email)
        assert reset_mail is not None
        attacker_reset_token = reset_mail["token"]

        # Verify tokens are distinct
        assert attacker_verify_token != attacker_reset_token

        # 3. Legitimate owner logs in via Google with verified email
        owner_google_sub = f"sub-owner-{uuid.uuid4().hex[:8]}"
        fake_id_info = {
            "iss": "accounts.google.com",
            "sub": owner_google_sub,
            "email": victim_email,
            "email_verified": True,
            "name": "Legitimate Owner",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_id_info):
            g_resp = await client.post("/api/v1/auth/google", json={"id_token": "valid-owner-token"})
            assert g_resp.status_code == 200
            owner_jwt = g_resp.json()["data"]["access_token"]
            owner_user_id = g_resp.json()["data"]["user_id"]
            assert owner_jwt is not None

        # 4. Attacker attempts:
        # a) Login with unverified password -> MUST FAIL (401)
        pw_login = await client.post("/api/v1/auth/login", json={"email": victim_email, "password": attacker_pw})
        assert pw_login.status_code == 401

        # b) Consume the outstanding verification token -> MUST FAIL (400)
        verify_attempt = await client.post("/api/v1/auth/verify-email", json={"token": attacker_verify_token})
        assert verify_attempt.status_code == 400

        # c) Consume the outstanding reset token -> MUST FAIL (400)
        reset_attempt = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": attacker_reset_token, "new_password": "NewAttackerPw123!"},
        )
        assert reset_attempt.status_code == 400

        # 5. Legitimate owner logs in again with Google -> SUCCEEDS with identical user_id
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_id_info):
            g_resp_2 = await client.post("/api/v1/auth/google", json={"id_token": "valid-owner-token-2"})
            assert g_resp_2.status_code == 200
            assert g_resp_2.json()["data"]["user_id"] == owner_user_id


@pytest.mark.asyncio
async def test_conflicting_google_identity_rejected():
    """Security: An account bound to one Google subject cannot be hijacked by another Google subject with the same email."""
    account_email = f"conflict_{uuid.uuid4().hex[:8]}@example.com"
    original_sub = f"sub-orig-{uuid.uuid4().hex[:8]}"
    impostor_sub = f"sub-impostor-{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. User signs in with original Google account
        orig_id_info = {
            "iss": "accounts.google.com",
            "sub": original_sub,
            "email": account_email,
            "email_verified": True,
            "name": "Original User",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=orig_id_info):
            res_orig = await client.post("/api/v1/auth/google", json={"id_token": "token-original"})
            assert res_orig.status_code == 200
            user_id = res_orig.json()["data"]["user_id"]

        # 2. Different Google subject signs in with the same email
        impostor_id_info = {
            "iss": "accounts.google.com",
            "sub": impostor_sub,
            "email": account_email,
            "email_verified": True,
            "name": "Impostor Account",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=impostor_id_info):
            res_impostor = await client.post("/api/v1/auth/google", json={"id_token": "token-impostor"})
            assert res_impostor.status_code == 409
            assert "already linked to a different Google account" in res_impostor.json()["detail"]

        # 3. Original Google user still logs in without issue
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=orig_id_info):
            res_orig_retry = await client.post("/api/v1/auth/google", json={"id_token": "token-original-retry"})
            assert res_orig_retry.status_code == 200
            assert res_orig_retry.json()["data"]["user_id"] == user_id


@pytest.mark.asyncio
async def test_google_login_email_backfill_does_not_collide_with_existing_account():
    """Security: Backfilling a placeholder Google user's email does not collide with an existing account."""
    existing_email = f"coll_target_{uuid.uuid4().hex[:8]}@example.com"
    google_sub = f"sub-backfill-{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Existing local verified user owns existing_email
        s_res = await client.post(
            "/api/v1/auth/signup",
            json={"email": existing_email, "password": "TargetPassword123!", "name": "Target Owner"},
        )
        assert s_res.status_code == 200
        sent = email_service.get_last_email_for(existing_email)
        v_res = await client.post("/api/v1/auth/verify-email", json={"token": sent["token"]})
        assert v_res.status_code == 200

        # 2. Google user registers with placeholder email first
        placeholder_info = {
            "iss": "accounts.google.com",
            "sub": google_sub,
            "email": f"{google_sub}@google.user",
            "email_verified": True,
            "name": "Placeholder User",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=placeholder_info):
            g_res = await client.post("/api/v1/auth/google", json={"id_token": "token-placeholder"})
            assert g_res.status_code == 200
            google_user_id = g_res.json()["data"]["user_id"]

        # 3. Later, Google user tries to authenticate with existing_email
        # FinEx should gracefully handle this without crashing or overwriting the existing user
        updated_google_info = {
            "iss": "accounts.google.com",
            "sub": google_sub,
            "email": existing_email,
            "email_verified": True,
            "name": "Placeholder User Updated",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=updated_google_info):
            g_res_update = await client.post("/api/v1/auth/google", json={"id_token": "token-updated"})
            assert g_res_update.status_code == 200
            # User ID must remain the Google user's own ID
            assert g_res_update.json()["data"]["user_id"] == google_user_id
