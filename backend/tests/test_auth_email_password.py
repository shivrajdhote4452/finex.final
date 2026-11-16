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
        assert body["data"]["sent"] is True
        assert body["data"]["email"] == test_email.lower()
        assert "verification link has been sent" in body["data"]["message"].lower()

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
async def test_signup_duplicate_email_safe_non_enumerating_response():
    """Test that duplicate signup returns safe 200 response identical to initial signup to prevent enumeration."""
    test_email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": test_email,
        "password": "Password123!",
        "name": "First Investor",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First signup (unregistered email)
        resp1 = await client.post("/api/v1/auth/signup", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()["data"]
        assert data1["sent"] is True

        # Verify initial user with their password
        email_sent_1 = email_service.get_last_email_for(test_email)
        assert email_sent_1 is not None
        verify_token = email_sent_1["metadata"]["token"]
        v_res = await client.post("/api/v1/auth/verify-email", json={"token": verify_token})
        assert v_res.status_code == 200

        # Login works with original password
        login1 = await client.post("/api/v1/auth/login", json={"email": test_email, "password": "Password123!"})
        assert login1.status_code == 200
        user_id = login1.json()["data"]["user_id"]

        # Second signup attempt with SAME email, different password (attacker or returning user)
        attacker_payload = {
            "email": test_email,
            "password": "AttackerPassword999!",
            "name": "Impostor",
        }
        resp2 = await client.post("/api/v1/auth/signup", json=attacker_payload)
        # MUST return identical 200 OK without leaking account existence
        assert resp2.status_code == 200
        data2 = resp2.json()["data"]
        assert data2["sent"] is True
        assert data2["message"] == data1["message"]

        # Credentials must NOT be modified
        bad_login = await client.post("/api/v1/auth/login", json={"email": test_email, "password": "AttackerPassword999!"})
        assert bad_login.status_code == 401
        assert bad_login.json()["detail"] == "Invalid email or password."

        # Original password still works
        good_login = await client.post("/api/v1/auth/login", json={"email": test_email, "password": "Password123!"})
        assert good_login.status_code == 200
        assert good_login.json()["data"]["user_id"] == user_id


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


@pytest.mark.asyncio
async def test_seed_user_placeholder_google_subject_upgraded_on_real_login():
    """Bug fix verification: Platform owner or seed user with placeholder 'google-sub-*'
    can log in with a real Google account without receiving 409 Conflict.
    Preserves existing user ID, profile, and data.
    """
    real_google_sub = "104829184719284918274"
    owner_email = "shivrajdhote4452@gmail.com"

    from backend.app.database import AsyncSessionLocal
    from backend.app.domain.user_store import user_store
    from backend.app.models.core import User
    from sqlalchemy import select

    # Ensure seed users exist in DB with placeholder google_subject
    await user_store.ensure_seed_users_db()
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == "usr-shivraj-001"))
        u = res.scalars().first()
        assert u is not None
        u.email = owner_email
        u.google_subject = "google-sub-shivraj-primary"
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Mock Google OAuth token verification returning real Google sub for the owner email
        real_id_info = {
            "iss": "accounts.google.com",
            "sub": real_google_sub,
            "email": owner_email,
            "email_verified": True,
            "name": "Shivraj Dhote",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=real_id_info):
            resp = await client.post("/api/v1/auth/google", json={"id_token": "token-real-google"})
            assert resp.status_code == 200, f"Expected 200 but got {resp.status_code}: {resp.text}"
            data = resp.json()["data"]
            assert data["user_id"] == "usr-shivraj-001"
            assert data["email"] == owner_email

        # Second login with the same real Google sub succeeds directly
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=real_id_info):
            resp_again = await client.post("/api/v1/auth/google", json={"id_token": "token-real-google-2"})
            assert resp_again.status_code == 200
            assert resp_again.json()["data"]["user_id"] == "usr-shivraj-001"

        # An impostor with a different real Google sub trying to claim the same email is rejected with 409
        impostor_info = {
            "iss": "accounts.google.com",
            "sub": "209482710492817294819",
            "email": owner_email,
            "email_verified": True,
            "name": "Impostor",
        }
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=impostor_info):
            resp_impostor = await client.post("/api/v1/auth/google", json={"id_token": "token-impostor"})
            assert resp_impostor.status_code == 409
            # Verify both detail and error.message exist and explain conflict clearly
            resp_json = resp_impostor.json()
            assert "detail" in resp_json
            assert "already linked to a different Google account" in resp_json["detail"]
            assert resp_json.get("error", {}).get("message") is not None


@pytest.mark.asyncio
async def test_error_envelope_contains_detail_and_structured_error():
    """Verify that HTTPExceptions return both standard detail and structured error envelope."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Trigger 400 Bad Request
        resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": "invalid-email", "password": "Password123!"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "valid email address is required" in data["detail"].lower()
        assert data.get("success") is False
        assert data.get("error", {}).get("message") is not None


@pytest.mark.asyncio
async def test_unregistered_email_signin_returns_safe_generic_401():
    """Verify that sign-in with an unregistered email returns safe generic 401 without enumeration."""
    unregistered_email = f"unregistered_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": unregistered_email, "password": "AnyPassword123!"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data.get("detail") == "Invalid email or password."
        assert data.get("success") is False


@pytest.mark.asyncio
async def test_google_only_user_signin_without_password_returns_safe_generic_401():
    """Verify that a user who registered via Google only (no password_hash) receives generic 401 on password login."""
    google_email = f"googleonly_{uuid.uuid4().hex[:8]}@example.com"
    id_info = {
        "iss": "accounts.google.com",
        "sub": f"google-sub-{uuid.uuid4().hex[:12]}",
        "email": google_email,
        "email_verified": True,
        "name": "Google User",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=id_info):
            g_resp = await client.post("/api/v1/auth/google", json={"id_token": "valid-token"})
            assert g_resp.status_code == 200

        # Attempt password sign-in without a set password
        p_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": google_email, "password": "RandomPassword123!"},
        )
        assert p_resp.status_code == 401
        assert p_resp.json().get("detail") == "Invalid email or password."


@pytest.mark.asyncio
async def test_forgot_password_unconfigured_smtp_truthful_response():
    """Verify that when SMTP is not configured in non-test mode, forgot-password truthfully returns sent: False."""
    from backend.app.config import get_settings

    settings = get_settings()
    email_service.disable_test_mode()
    try:
        with patch.object(settings, "SMTP_HOST", ""):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "anyone@example.com"},
                )
                assert resp.status_code == 200
                data = resp.json().get("data", {})
                assert data.get("sent") is False
                assert "transactional email is not configured" in data.get("message", "").lower()
                assert data.get("delivery_status") == "smtp_not_configured"
    finally:
        email_service.enable_test_mode()


@pytest.mark.asyncio
async def test_resend_verification_unconfigured_smtp_truthful_response():
    """Verify that when SMTP is not configured in non-test mode, resend-verification truthfully returns sent: False."""
    from backend.app.config import get_settings

    settings = get_settings()
    email_service.disable_test_mode()
    try:
        with patch.object(settings, "SMTP_HOST", ""):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/auth/resend-verification",
                    json={"email": "anyone@example.com"},
                )
                assert resp.status_code == 200
                data = resp.json().get("data", {})
                assert data.get("sent") is False
                assert "transactional email is not configured" in data.get("message", "").lower()
                assert data.get("delivery_status") == "smtp_not_configured"
    finally:
        email_service.enable_test_mode()


@pytest.mark.asyncio
async def test_existing_google_user_signup_conflict_and_password_addition_paths():
    """Verify how an existing Google user interacts with signup, forgot-password, and set-password:
    1. Unauthenticated signup returns 409 Conflict with generic message (no provider leak).
    2. Attempting to signup does NOT modify user password or credentials.
    3. Legitimate user can add password via unauthenticated forgot-password reset link.
    4. Legitimate user can add password via authenticated in-app /set-password.
    5. After setting a password, user can sign in via either Google or email/password with identical user ID.
    """
    google_email = f"googleguy_{uuid.uuid4().hex[:8]}@example.com"
    google_sub = f"sub-googleguy-{uuid.uuid4().hex[:10]}"
    fake_id_info = {
        "iss": "accounts.google.com",
        "sub": google_sub,
        "email": google_email,
        "email_verified": True,
        "name": "Google Guy",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register and sign in with Google
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_id_info):
            g_resp = await client.post("/api/v1/auth/google", json={"id_token": "valid-token-1"})
            assert g_resp.status_code == 200
            google_user_id = g_resp.json()["data"]["user_id"]

        # 2. Unauthenticated attacker or user tries to signup with that email
        signup_resp = await client.post(
            "/api/v1/auth/signup",
            json={"email": google_email, "password": "AttackerPassword123!", "name": "Fake Name"},
        )
        assert signup_resp.status_code == 200
        data_s = signup_resp.json()["data"]
        assert data_s["sent"] is True
        assert "verification link has been sent" in data_s["message"].lower()

        # 3. Password was NOT set by signup attempt
        pw_login = await client.post(
            "/api/v1/auth/login",
            json={"email": google_email, "password": "AttackerPassword123!"},
        )
        assert pw_login.status_code == 401
        assert pw_login.json()["detail"] == "Invalid email or password."

        # 4. User adds password via forgot-password flow (requires email access proof)
        forgot_resp = await client.post("/api/v1/auth/forgot-password", json={"email": google_email})
        assert forgot_resp.status_code == 200
        sent = email_service.get_last_email_for(google_email)
        assert sent is not None
        reset_token = sent["metadata"]["token"]

        reset_resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": "LegitPassword123!"},
        )
        assert reset_resp.status_code == 200

        # 5. User can now sign in via email/password
        legit_login = await client.post(
            "/api/v1/auth/login",
            json={"email": google_email, "password": "LegitPassword123!"},
        )
        assert legit_login.status_code == 200
        assert legit_login.json()["data"]["user_id"] == google_user_id

        # 6. User can also still sign in via Google
        with patch("backend.app.routers.auth.google_id_token.verify_oauth2_token", return_value=fake_id_info):
            g_resp_again = await client.post("/api/v1/auth/google", json={"id_token": "valid-token-2"})
            assert g_resp_again.status_code == 200
            assert g_resp_again.json()["data"]["user_id"] == google_user_id


@pytest.mark.asyncio
async def test_signup_unconfigured_smtp_truthful_response():
    """Verify that when SMTP is not configured in non-test mode, signup truthfully returns sent: False without enumeration."""
    from backend.app.config import get_settings

    settings = get_settings()
    email_service.disable_test_mode()
    try:
        with patch.object(settings, "SMTP_HOST", ""):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/auth/signup",
                    json={"email": "anyone_signup@example.com", "password": "Password123!", "name": "User"},
                )
                assert resp.status_code == 200
                data = resp.json().get("data", {})
                assert data.get("sent") is False
                assert "transactional email is not configured" in data.get("message", "").lower()
                assert data.get("delivery_status") == "smtp_not_configured"
    finally:
        email_service.enable_test_mode()





@pytest.mark.asyncio
async def test_signup_delivery_failure_new_and_existing_accounts_truthful_and_non_enumerating():
    """Verify that when SMTP delivery fails or times out:
    1. New account receives sent: False with explicit mail server issue message.
    2. Existing account receives an IDENTICAL sent: False response (no account enumeration).
    3. User entity was created for the new user, and existing user credentials were NOT overwritten.
    """
    from backend.app.config import get_settings
    from backend.app.domain.user_store import user_store

    settings = get_settings()
    new_email = f"smtp_fail_new_{uuid.uuid4().hex[:8]}@example.com"
    existing_email = f"smtp_fail_exist_{uuid.uuid4().hex[:8]}@example.com"
    orig_password = "OriginalPassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 0: Create existing user cleanly first
        init_res = await client.post(
            "/api/v1/auth/signup",
            json={"email": existing_email, "password": orig_password, "name": "Existing User"},
        )
        assert init_res.status_code == 200
        existing_user_rec = await user_store.get_user_by_email_db(existing_email)
        assert existing_user_rec is not None
        saved_pw_hash = existing_user_rec.password_hash

        # Mock email_service failure (simulate timeout or SMTP socket error)
        failed_result = {"status": "failed", "delivered": False, "to": "mock", "error": "SMTPConnectionTimeout"}
        with patch.object(settings, "SMTP_HOST", "smtp.live.example.com"):
            with patch.object(email_service, "send_verification_email", return_value=failed_result):
                with patch.object(email_service, "send_existing_account_notification", return_value=failed_result):
                    # 1. New account signup under failure
                    resp_new = await client.post(
                        "/api/v1/auth/signup",
                        json={"email": new_email, "password": "NewUserPassword123!", "name": "New User"},
                    )
                    assert resp_new.status_code == 200
                    data_new = resp_new.json()["data"]
                    assert data_new["sent"] is False
                    assert data_new["delivery_status"] == "failed"
                    assert "could not be delivered due to a mail server issue" in data_new["message"].lower()

                    # 2. Existing account signup under failure
                    resp_exist = await client.post(
                        "/api/v1/auth/signup",
                        json={"email": existing_email, "password": "AttackerCandidatePw123!", "name": "Attacker"},
                    )
                    assert resp_exist.status_code == 200
                    data_exist = resp_exist.json()["data"]
                    assert data_exist["sent"] is False
                    assert data_exist["delivery_status"] == "failed"
                    assert data_exist["message"] == data_new["message"]

        # 3. Verify user entity creation & credential immutability
        created_new_user = await user_store.get_user_by_email_db(new_email)
        assert created_new_user is not None
        assert created_new_user.email_verified is False

        # Existing user password was NOT overwritten
        check_existing = await user_store.get_user_by_email_db(existing_email)
        assert check_existing.password_hash == saved_pw_hash


@pytest.mark.asyncio
async def test_unverified_user_can_retry_and_verify_after_delivery_failure():
    """Verify that an unverified user whose initial signup email failed can retry via resend-verification
    or duplicate signup once SMTP is restored, activate their account, and login with original password.
    """
    from backend.app.config import get_settings

    settings = get_settings()
    user_email = f"retry_flow_{uuid.uuid4().hex[:8]}@example.com"
    user_password = "RetryFlowPassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Initial signup fails due to SMTP failure
        failed_result = {"status": "failed", "delivered": False, "to": user_email, "error": "SMTPTimeout"}
        with patch.object(settings, "SMTP_HOST", "smtp.live.example.com"):
            with patch.object(email_service, "send_verification_email", return_value=failed_result):
                initial_signup = await client.post(
                    "/api/v1/auth/signup",
                    json={"email": user_email, "password": user_password, "name": "Retry User"},
                )
                assert initial_signup.status_code == 200
                assert initial_signup.json()["data"]["sent"] is False

        # Cannot log in yet because unverified
        unver_login = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": user_password},
        )
        assert unver_login.status_code == 403
        assert "not verified" in unver_login.json()["detail"].lower()

        # 2. Mail server recovers: user requests resend verification
        resend_resp = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": user_email},
        )
        assert resend_resp.status_code == 200
        assert resend_resp.json()["data"]["sent"] is True

        sent_mail = email_service.get_last_email_for(user_email)
        assert sent_mail is not None
        token = sent_mail["metadata"]["token"]

        # 3. User verifies email
        verify_resp = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["data"]["verified"] is True

        # 4. User logs in with original password successfully
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": user_password},
        )
        assert login_resp.status_code == 200
        assert login_resp.json()["data"]["access_token"] is not None


@pytest.mark.asyncio
async def test_pre_account_takeover_prevention_on_unverified_signup():
    """OWASP Pre-Account Takeover Defense Regression Test.

    Scenario:
    1. Attacker initiates signup with victim's email and attacker-chosen password. Account remains unverified.
    2. Later, legitimate owner attempts signup with the same email and a different password.
       - Token 1 (attacker's attempt) must be invalidated and fail if clicked.
    3. Owner receives and clicks the verification link (Token 2) produced by the second attempt.
    4. Attacker's original password MUST NOT be able to log in (401 Unauthorized).
    5. Legitimate owner's password MUST be able to log in successfully (200 OK).
    6. Token 2 replay must be rejected (400 Bad Request).
    7. Subsequent duplicate signups on the verified account must not overwrite credentials.
    """
    email_service.enable_test_mode()
    email_service.clear_sent_emails()

    victim_email = f"takeover_victim_{uuid.uuid4().hex[:8]}@example.com"
    attacker_pw = "AttackerMalicious123!"
    owner_pw = "OwnerLegitimate456!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Attacker starts signup using victim's email
        r1 = await client.post(
            "/api/v1/auth/signup",
            json={"email": victim_email, "password": attacker_pw, "name": "Attacker Impostor"},
        )
        assert r1.status_code == 200
        mail1 = email_service.get_last_email_for(victim_email)
        assert mail1 is not None
        token1 = mail1["metadata"]["token"]

        # Attacker cannot log in because unverified
        r1_login = await client.post("/api/v1/auth/login", json={"email": victim_email, "password": attacker_pw})
        assert r1_login.status_code == 403

        # Step 2: Later, legitimate owner attempts signup with same email and different password
        r2 = await client.post(
            "/api/v1/auth/signup",
            json={"email": victim_email, "password": owner_pw, "name": "Legitimate Owner"},
        )
        assert r2.status_code == 200
        mail2 = email_service.get_last_email_for(victim_email)
        assert mail2 is not None
        token2 = mail2["metadata"]["token"]
        assert token1 != token2

        # Step 3: Owner receives and clicks verification link (Token 2)
        r3_verify = await client.post("/api/v1/auth/verify-email", json={"token": token2})
        assert r3_verify.status_code == 200
        assert r3_verify.json()["data"]["verified"] is True

        # Stale Token 1 (from attacker attempt) must be invalidated once Token 2 is verified
        r1_stale = await client.post("/api/v1/auth/verify-email", json={"token": token1})
        assert r1_stale.status_code == 400
        assert "Invalid, expired, or previously used" in r1_stale.json()["detail"]

        # Step 4: Attacker tries to sign in with original attacker_pw -> MUST BE REJECTED
        r4_attacker_login = await client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": attacker_pw},
        )
        assert r4_attacker_login.status_code == 401
        assert "Invalid email or password" in r4_attacker_login.json()["detail"]

        # Legitimate owner logs in with owner_pw -> MUST SUCCEED
        r4_owner_login = await client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": owner_pw},
        )
        assert r4_owner_login.status_code == 200
        assert r4_owner_login.json()["data"]["access_token"] is not None
        assert r4_owner_login.json()["data"]["email"] == victim_email

        # Token 2 replay check
        r2_replay = await client.post("/api/v1/auth/verify-email", json={"token": token2})
        assert r2_replay.status_code == 400

        # Step 5: Attacker attempts duplicate signup on already verified account
        r5 = await client.post(
            "/api/v1/auth/signup",
            json={"email": victim_email, "password": "AttackerSubsequent999!", "name": "Attacker Impostor 2"},
        )
        assert r5.status_code == 200
        # Attacker's subsequent password must not be active
        r5_attacker_login = await client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": "AttackerSubsequent999!"},
        )
        assert r5_attacker_login.status_code == 401
        # Owner's password is still valid and untouched
        r5_owner_login = await client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": owner_pw},
        )
        assert r5_owner_login.status_code == 200


@pytest.mark.asyncio
async def test_recipient_specific_smtp_failure_symmetry_and_behavior():
    """Verify that recipient-specific SMTP failures (e.g. 550 Mailbox not found / rejected)
    yield symmetric safe responses across new, unverified, and verified accounts.
    """
    from backend.app.config import get_settings

    settings = get_settings()

    new_email = f"smtp_fail_new_{uuid.uuid4().hex[:8]}@example.com"
    existing_unverified = f"smtp_fail_unver_{uuid.uuid4().hex[:8]}@example.com"
    existing_verified = f"smtp_fail_ver_{uuid.uuid4().hex[:8]}@example.com"
    pw = "SmtpFailTestPassword123!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Pre-seed existing unverified account
        await client.post("/api/v1/auth/signup", json={"email": existing_unverified, "password": pw})

        # Pre-seed existing verified account
        await client.post("/api/v1/auth/signup", json={"email": existing_verified, "password": pw})
        v_mail = email_service.get_last_email_for(existing_verified)
        assert v_mail is not None
        v_token = v_mail["metadata"]["token"]
        await client.post("/api/v1/auth/verify-email", json={"token": v_token})

        recipient_550_failure = {
            "status": "failed",
            "delivered": False,
            "error": "550 5.1.1 <recipient>: Recipient address rejected: User unknown in virtual mailbox table",
        }

        with patch.object(settings, "SMTP_HOST", "smtp.live.example.com"):
            with patch.object(email_service, "send_verification_email", return_value=recipient_550_failure):
                with patch.object(email_service, "send_existing_account_notification", return_value=recipient_550_failure):
                    # 1. New account registration with recipient-specific SMTP failure
                    resp_new = await client.post(
                        "/api/v1/auth/signup",
                        json={"email": new_email, "password": pw, "name": "New User"},
                    )
                    assert resp_new.status_code == 200
                    data_new = resp_new.json()["data"]
                    assert data_new["sent"] is False
                    assert data_new["delivery_status"] == "failed"
                    assert "could not be delivered" in data_new["message"]

                    # 2. Existing unverified account signup with recipient-specific SMTP failure
                    resp_unver = await client.post(
                        "/api/v1/auth/signup",
                        json={"email": existing_unverified, "password": pw, "name": "Unver User"},
                    )
                    assert resp_unver.status_code == 200
                    data_unver = resp_unver.json()["data"]
                    assert data_unver["sent"] is False
                    assert data_unver["delivery_status"] == "failed"
                    assert "could not be delivered" in data_unver["message"]

                    # 3. Existing verified account signup with recipient-specific SMTP failure
                    resp_ver = await client.post(
                        "/api/v1/auth/signup",
                        json={"email": existing_verified, "password": pw, "name": "Ver User"},
                    )
                    assert resp_ver.status_code == 200
                    data_ver = resp_ver.json()["data"]
                    assert data_ver["sent"] is False
                    assert data_ver["delivery_status"] == "failed"
                    assert "could not be delivered" in data_ver["message"]

                    # Response envelopes must be symmetric
                    assert data_new["message"] == data_unver["message"] == data_ver["message"]
                    assert data_new["sent"] == data_unver["sent"] == data_ver["sent"]
                    assert data_new["delivery_status"] == data_unver["delivery_status"] == data_ver["delivery_status"]


@pytest.mark.asyncio
async def test_concurrent_verification_click_during_email_dispatch():
    """Verify that if an owner clicks their verification link WHILE a subsequent duplicate
    signup attempt is in the middle of slow email dispatch, the verification securely activates
    the owner's password and the subsequent signup cannot overwrite it or compromise the account.
    """
    import asyncio

    email_service.enable_test_mode()
    email_service.clear_sent_emails()

    victim_email = f"race_verify_{uuid.uuid4().hex[:8]}@example.com"
    attacker_pw = "AttackerRacePw123!"
    owner_pw = "OwnerRacePw456!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Owner initiates signup cleanly
        r0 = await client.post(
            "/api/v1/auth/signup",
            json={"email": victim_email, "password": owner_pw, "name": "Legitimate Owner"},
        )
        assert r0.status_code == 200
        mail0 = email_service.get_last_email_for(victim_email)
        assert mail0 is not None
        owner_token = mail0["metadata"]["token"]

        # Step 2: Attacker initiates duplicate signup. We simulate slow SMTP dispatch
        # during which the legitimate owner simultaneously clicks verification on owner_token.
        original_send = email_service.send_verification_email

        async def slow_send_and_verify(*args, **kwargs):
            if kwargs.get("name") == "Attacker":
                # Interleave: owner clicks verification during attacker's SMTP dispatch
                v_res = await client.post("/api/v1/auth/verify-email", json={"token": owner_token})
                assert v_res.status_code == 200
                await asyncio.sleep(0.1)
            return await original_send(*args, **kwargs)

        email_service.send_verification_email = slow_send_and_verify
        try:
            r_att = await client.post(
                "/api/v1/auth/signup",
                json={"email": victim_email, "password": attacker_pw, "name": "Attacker"},
            )
            assert r_att.status_code == 200
        finally:
            email_service.send_verification_email = original_send

        # Step 3: Attacker tries to log in with attacker_pw -> MUST FAIL (401)
        att_login = await client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": attacker_pw},
        )
        assert att_login.status_code == 401

        # Step 4: Owner logs in with owner_pw -> MUST SUCCEED (200)
        own_login = await client.post(
            "/api/v1/auth/login",
            json={"email": victim_email, "password": owner_pw},
        )
        assert own_login.status_code == 200
        assert own_login.json()["data"]["access_token"] is not None


@pytest.mark.asyncio
async def test_overlapping_concurrent_duplicate_signups():
    """Verify that when overlapping concurrent signup requests arrive for an unverified account,
    each verification token cryptographically binds its own intended password, and row-level
    locking guarantees that verifying a specific token activates ONLY its corresponding password.
    """
    import asyncio

    email_service.enable_test_mode()
    email_service.clear_sent_emails()

    target_email = f"concurrent_dups_{uuid.uuid4().hex[:8]}@example.com"
    r_seed = await AsyncClient(transport=ASGITransport(app=app), base_url="http://test").post(
        "/api/v1/auth/signup", json={"email": target_email, "password": "SeedPassword123!"}
    )
    assert r_seed.status_code == 200

    att_token = None
    own_token = None
    original_send = email_service.send_verification_email

    async def capture_tokens(*args, **kwargs):
        nonlocal att_token, own_token
        name = kwargs.get("name")
        token = kwargs.get("raw_token")
        if name == "Attacker":
            att_token = token
            await asyncio.sleep(0.15)
        elif name == "Owner":
            own_token = token
        return await original_send(*args, **kwargs)

    email_service.send_verification_email = capture_tokens

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            task_a = asyncio.create_task(
                client.post(
                    "/api/v1/auth/signup",
                    json={"email": target_email, "password": "AttackerOverlapping123!", "name": "Attacker"},
                )
            )
            await asyncio.sleep(0.01)
            task_b = asyncio.create_task(
                client.post(
                    "/api/v1/auth/signup",
                    json={"email": target_email, "password": "OwnerOverlapping456!", "name": "Owner"},
                )
            )

            res_a, res_b = await asyncio.gather(task_a, task_b)
            assert res_a.status_code == 200
            assert res_b.status_code == 200
            assert own_token is not None
            assert att_token is not None
        finally:
            email_service.send_verification_email = original_send

        # Owner verifies with Owner's token
        v_res = await client.post("/api/v1/auth/verify-email", json={"token": own_token})
        assert v_res.status_code == 200

        # Attacker cannot log in
        login_att = await client.post(
            "/api/v1/auth/login",
            json={"email": target_email, "password": "AttackerOverlapping123!"},
        )
        assert login_att.status_code == 401

        # Owner logs in successfully
        login_own = await client.post(
            "/api/v1/auth/login",
            json={"email": target_email, "password": "OwnerOverlapping456!"},
        )
        assert login_own.status_code == 200
        assert login_own.json()["data"]["access_token"] is not None


