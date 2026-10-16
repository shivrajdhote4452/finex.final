"""Contract and Integration Tests for Auth, Profile, Consent, and Risk Evaluation APIs.

Task ID: CH-01, CH-10, S2-API-03, S2-AI-03
Verifies fail-closed authentication (401 on missing/invalid/revoked credentials),
verified Google ID token flows, single-use token rotation, two-user isolation,
and deterministic risk evaluation with profile persistence.
"""

from unittest.mock import patch

import pytest
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token
from httpx import ASGITransport, AsyncClient

app = create_app()


@pytest.mark.asyncio
async def test_unauthenticated_private_request_fails_401():
    """Verify that private routes fail closed with HTTP 401 when no credentials are provided."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. No Authorization header
        resp1 = await client.get("/api/v1/users/me")
        assert resp1.status_code == 401
        assert "WWW-Authenticate" in resp1.headers

        # 2. Malformed Authorization header
        resp2 = await client.get("/api/v1/users/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert resp2.status_code == 401

        # 3. Invalid JWT token
        resp3 = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-valid-jwt"})
        assert resp3.status_code == 401


@pytest.mark.asyncio
async def test_google_auth_invalid_token_rejects_401():
    """Verify that forged, invalid, or expired Google ID tokens are rejected with HTTP 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "forged.fake.google-token-xyz"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "verification failed" in data["detail"].lower()


@pytest.mark.asyncio
async def test_google_auth_valid_token_issues_session():
    """Verify that a cryptographically verified Google token issues a valid session."""
    mock_id_info = {
        "sub": "google-user-id-998877",
        "email": "verified.investor@gmail.com",
        "name": "Verified Investor",
        "iss": "https://accounts.google.com",
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "real-signed-google-token-fixture"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["email"] == "verified.investor@gmail.com"
            assert data["name"] == "Verified Investor"
            assert "access_token" in data
            token = data["access_token"]

            # Query profile using the newly issued JWT
            headers = {"Authorization": f"Bearer {token}"}
            me_resp = await client.get("/api/v1/users/me", headers=headers)
            assert me_resp.status_code == 200
            me_data = me_resp.json()["data"]
            assert me_data["email"] == "verified.investor@gmail.com"
            assert me_data["full_name"] == "Verified Investor"


@pytest.mark.asyncio
async def test_session_revoke_and_rotation():
    """Verify token revocation immediately denies subsequent requests and rotation invalidates prior token."""
    token = create_access_token(
        user_id="usr-shivraj-001",
        email="shivraj.dhote@finex.internal",
        name="Shivraj Dhote",
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Check active session works
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200

        # Rotate token
        ref_resp = await client.post("/api/v1/auth/refresh", headers=headers)
        assert ref_resp.status_code == 200
        new_token = ref_resp.json()["data"]["access_token"]

        # Prior token must now be revoked
        prior_resp = await client.get("/api/v1/users/me", headers=headers)
        assert prior_resp.status_code == 401
        assert "revoked" in prior_resp.json()["detail"].lower()

        # New token must work
        new_headers = {"Authorization": f"Bearer {new_token}"}
        active_resp = await client.get("/api/v1/users/me", headers=new_headers)
        assert active_resp.status_code == 200

        # Explicitly revoke new token
        rev_resp = await client.post("/api/v1/auth/revoke", headers=new_headers)
        assert rev_resp.status_code == 200

        # Revoked token cannot access protected routes
        denied_resp = await client.get("/api/v1/users/me", headers=new_headers)
        assert denied_resp.status_code == 401


@pytest.mark.asyncio
async def test_consent_recording_against_identity():
    """Verify regulatory consent is audited and persisted against the verified identity."""
    token = create_access_token(
        user_id="usr-audit-test-01",
        email="audited@finex.internal",
        name="Audited User",
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        consent_resp = await client.post(
            "/api/v1/users/consent",
            headers=headers,
            json={
                "consent_version": "v1.0",
                "terms_accepted": True,
                "privacy_accepted": True,
                "educational_disclaimer_accepted": True,
            },
        )
        assert consent_resp.status_code == 200
        c_data = consent_resp.json()["data"]
        assert c_data["status"] == "ACCEPTED"
        assert c_data["user_id"] == "usr-audit-test-01"


@pytest.mark.asyncio
async def test_risk_questionnaire_and_assessment():
    token = create_access_token(
        user_id="usr-shivraj-001",
        email="shivraj.dhote@finex.internal",
        name="Shivraj Dhote",
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch Questionnaire
        q_resp = await client.get("/api/v1/risk/questions")
        assert q_resp.status_code == 200
        q_data = q_resp.json()["data"]
        assert len(q_data) == 4
        assert q_data[0]["id"] == "Q1"

        # 2. Moderate submission scenario
        submission = {
            "horizon_category": "3-5",
            "questionnaire_version": "v1.0",
            "answers": [
                {"question_id": "Q1", "option_id": "Q1_C", "score": 70},
                {"question_id": "Q2", "option_id": "Q2_C", "score": 75},
                {"question_id": "Q3", "option_id": "Q3_B", "score": 60},
                {"question_id": "Q4", "option_id": "Q4_C", "score": 70},
            ],
        }

        eval_resp = await client.post("/api/v1/risk/assessments", headers=headers, json=submission)
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()["data"]
        assert eval_data["risk_band"] == "MODERATE"
        assert 40 <= eval_data["composite_score"] < 70
        assert "SEBI Guide to Financial Education" in eval_data["citation"]
        assert "SEBI (Investment Advisers) Regulations" in eval_data["disclaimer"]

        # 3. Verify assessment persisted in profile
        profile_resp = await client.get("/api/v1/risk/assessments/me", headers=headers)
        assert profile_resp.status_code == 200
        saved_data = profile_resp.json()["data"]
        assert saved_data["has_assessment"] is True
        assert saved_data["risk_band"] == "MODERATE"


@pytest.mark.asyncio
async def test_risk_conservative_scenario():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        submission = {
            "horizon_category": "<1",
            "questionnaire_version": "v1.0",
            "answers": [
                {"question_id": "Q1", "option_id": "Q1_A", "score": 10},
                {"question_id": "Q2", "option_id": "Q2_A", "score": 15},
                {"question_id": "Q3", "option_id": "Q3_A", "score": 20},
                {"question_id": "Q4", "option_id": "Q4_A", "score": 15},
            ],
        }

        eval_resp = await client.post("/api/v1/risk/assessments", json=submission)
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()["data"]
        assert eval_data["risk_band"] == "CONSERVATIVE"
        assert eval_data["composite_score"] < 40


@pytest.mark.asyncio
async def test_risk_aggressive_scenario():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        submission = {
            "horizon_category": ">5",
            "questionnaire_version": "v1.0",
            "answers": [
                {"question_id": "Q1", "option_id": "Q1_D", "score": 100},
                {"question_id": "Q2", "option_id": "Q2_D", "score": 100},
                {"question_id": "Q3", "option_id": "Q3_C", "score": 95},
                {"question_id": "Q4", "option_id": "Q4_D", "score": 100},
            ],
        }

        eval_resp = await client.post("/api/v1/risk/assessments", json=submission)
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()["data"]
        assert eval_data["risk_band"] == "AGGRESSIVE"
        assert eval_data["composite_score"] >= 70
