"""Contract and Integration Tests for Auth, Profile, Consent, and Risk Evaluation APIs.

Task ID: S2-API-03, S2-AI-03
"""

import pytest
from backend.app.factory import create_app
from httpx import ASGITransport, AsyncClient

app = create_app()


@pytest.mark.asyncio
async def test_google_auth_and_profile_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Authenticate with Google OAuth ID token
        auth_resp = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "mock-google-id-token-xyz", "email": "shivraj@finex.local", "name": "Shivraj Dhote"},
        )
        assert auth_resp.status_code == 200
        auth_json = auth_resp.json()
        assert auth_json["success"] is True
        assert "access_token" in auth_json["data"]
        token = auth_json["data"]["access_token"]
        assert auth_json["data"]["email"] == "shivraj@finex.local"

        # 2. Query /users/me using the issued JWT
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/api/v1/users/me", headers=headers)
        assert me_resp.status_code == 200
        me_json = me_resp.json()
        assert me_json["data"]["full_name"] == "Shivraj Dhote"
        assert me_json["data"]["onboarding_completed"] is True

        # 3. Submit Consent record
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
        consent_json = consent_resp.json()
        assert consent_json["data"]["status"] == "ACCEPTED"
        assert consent_json["data"]["consent_version"] == "v1.0"


@pytest.mark.asyncio
async def test_risk_questionnaire_and_assessment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch Questionnaire
        q_resp = await client.get("/api/v1/risk/questions")
        assert q_resp.status_code == 200
        q_data = q_resp.json()["data"]
        assert len(q_data) == 4
        assert q_data[0]["id"] == "Q1"

        # 2. Moderate submission scenario (Medium 3-5y horizon, balanced answers)
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

        eval_resp = await client.post("/api/v1/risk/assessments", json=submission)
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()["data"]
        assert eval_data["risk_band"] == "MODERATE"
        assert 40 <= eval_data["composite_score"] < 70
        assert "SEBI Guide to Financial Education" in eval_data["citation"]
        assert "SEBI (Investment Advisers) Regulations" in eval_data["disclaimer"]


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
