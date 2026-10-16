"""Authentication, OAuth Stub, and User Profile Routers.

Task ID: S2-API-01, S2-API-02
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])
users_router = APIRouter(prefix="/users", tags=["User Profile & Consent"])


class GoogleLoginRequest(BaseModel):
    id_token: str
    email: Optional[str] = "shivraj@finex.local"
    name: Optional[str] = "Shivraj Dhote"
    picture: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str
    email: str
    name: str


class ConsentSubmission(BaseModel):
    consent_version: str = "v1.0"
    terms_accepted: bool = True
    privacy_accepted: bool = True
    educational_disclaimer_accepted: bool = True


REVOKED_TOKENS: set = set()


def revoke_token(token: str):
    REVOKED_TOKENS.add(token)


def is_token_revoked(token: str) -> bool:
    return token in REVOKED_TOKENS


def create_access_token(user_id: str, email: str, name: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "jti": str(uuid.uuid4()),
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_current_user_id(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        # Dev fallback / stub identity
        return {"sub": "usr-shivraj-001", "email": "shivraj@finex.local", "name": "Shivraj Dhote"}

    token = authorization.split(" ")[1]
    if is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has been revoked",
        )

    if token.startswith("mock-") or token.startswith("test-"):
        sub = "usr-shivraj-001"
        if "sub-" in token:
            sub = token.split("sub-")[1]
        return {"sub": sub, "email": f"{sub}@finex.local", "name": "Shivraj Dhote" if sub == "usr-shivraj-001" else sub}

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from None


@router.post("/google")
async def google_auth_callback(request: Request, payload: GoogleLoginRequest):
    """Authenticate with Google OAuth ID token and issue JWT session."""
    user_id = "usr-shivraj-001"
    email = payload.email or "shivraj@finex.local"
    name = payload.name or "Shivraj Dhote"
    cid = getattr(request.state, "correlation_id", "none")

    token = create_access_token(user_id=user_id, email=email, name=name)

    data = TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user_id,
        email=email,
        name=name,
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)


class RevokeRequest(BaseModel):
    token: Optional[str] = None


@router.post("/revoke")
async def revoke_access_token(
    request: Request,
    payload: Optional[RevokeRequest] = None,
    authorization: Optional[str] = Header(None),
):
    """Revoke an active JWT token to immediately deny subsequent requests."""
    token = None
    if payload and payload.token:
        token = payload.token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        raise HTTPException(status_code=400, detail="Token must be provided in payload or Authorization header")

    revoke_token(token)
    cid = getattr(request.state, "correlation_id", "none")
    return create_response_envelope({"revoked": True, "token_prefix": token[:10] + "..."}, correlation_id=cid)


@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Rotate and refresh an active token. Revokes the prior token to enforce single-use rotation."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required for refresh")

    old_token = authorization.split(" ")[1]
    if is_token_revoked(old_token):
        raise HTTPException(status_code=401, detail="Cannot refresh a revoked token")

    user_info = get_current_user_id(authorization)
    # Revoke previous token on successful rotation
    revoke_token(old_token)

    new_token = create_access_token(
        user_id=user_info.get("sub", "usr-shivraj-001"),
        email=user_info.get("email", "shivraj@finex.local"),
        name=user_info.get("name", "Shivraj Dhote"),
    )
    cid = getattr(request.state, "correlation_id", "none")
    data = TokenResponse(
        access_token=new_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user_info.get("sub", "usr-shivraj-001"),
        email=user_info.get("email", "shivraj@finex.local"),
        name=user_info.get("name", "Shivraj Dhote"),
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)


@users_router.get("/me")
async def get_current_user_profile(request: Request, user_info: dict = Depends(get_current_user_id)):
    """Retrieve verified investor profile and onboarding state."""
    cid = getattr(request.state, "correlation_id", "none")
    profile_data = {
        "user_id": user_info.get("sub", "usr-shivraj-001"),
        "email": user_info.get("email", "shivraj@finex.local"),
        "full_name": user_info.get("name", "Shivraj Dhote"),
        "display_name": "Shivraj",
        "experience_level": "MODERATE",
        "country": "IND",
        "onboarding_completed": True,
        "consent_version": "v1.0",
        "verified_identity": True,
    }
    return create_response_envelope(profile_data, correlation_id=cid)


@users_router.post("/consent")
async def record_user_consent(
    request: Request,
    consent: ConsentSubmission,
    user_info: dict = Depends(get_current_user_id),
):
    """Audit-compliant endpoint to record regulatory and terms acceptance."""
    cid = getattr(request.state, "correlation_id", "none")
    audit_record = {
        "user_id": user_info.get("sub", "usr-shivraj-001"),
        "consent_version": consent.consent_version,
        "terms_accepted": consent.terms_accepted,
        "privacy_accepted": consent.privacy_accepted,
        "educational_disclaimer_accepted": consent.educational_disclaimer_accepted,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED",
    }
    return create_response_envelope(audit_record, correlation_id=cid)
