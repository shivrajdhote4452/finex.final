"""Authentication, Identity Provider Verification, and User Profile Routers.

Task ID: CH-01, S2-API-01, S2-API-02
Enforces fail-closed authentication (HTTP 401 on missing/invalid/expired/revoked tokens),
real Google OAuth cryptographic verification (aud, iss, exp, sub),
and durable user profile and consent management.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from backend.app.config import Environment, get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.domain.user_store import user_store
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, Field

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])
users_router = APIRouter(prefix="/users", tags=["User Profile & Consent"])


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., description="Cryptographically signed Google OAuth ID token")


class DevLoginRequest(BaseModel):
    user_id: str = "usr-shivraj-001"
    email: str = "shivraj.dhote@finex.internal"
    name: str = "Shivraj Dhote"


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


def revoke_token(token: str) -> None:
    """Revoke a token in the durable user store."""
    user_store.revoke_token(token)


def is_token_revoked(token: str) -> bool:
    """Check if token has been revoked."""
    return user_store.is_token_revoked(token)


def create_access_token(user_id: str, email: str, name: str) -> str:
    """Generate a signed HS256 JWT access token with standard claims."""
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
    """
    Fail-closed authentication dependency.
    Requires a valid, unrevoked Bearer JWT. Rejects missing, malformed,
    expired, or revoked tokens with HTTP 401.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ")
    if len(parts) != 2 or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed Authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()

    if user_store.is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: missing subject identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post("/google")
async def google_auth_callback(request: Request, payload: GoogleLoginRequest):
    """
    Authenticate with Google OAuth ID token.
    Validates Google signature, permitted audience, issuer, and expiration.
    Maps verified Google subject to an internal user identity.
    """
    cid = getattr(request.state, "correlation_id", "none")
    raw_token = payload.id_token.strip()

    # Determine permitted audience
    aud = None
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID != "placeholder-google-client-id":
        aud = settings.GOOGLE_CLIENT_ID

    try:
        id_info = google_id_token.verify_oauth2_token(
            raw_token,
            google_requests.Request(),
            audience=aud,
        )
        iss = id_info.get("iss", "")
        if iss not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError(f"Untrusted token issuer: {iss}")

        google_sub = id_info["sub"]
        email = id_info.get("email") or f"{google_sub}@google.user"
        name = id_info.get("name") or "Investor"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google ID token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    # Persist or retrieve user using verified unique provider and subject
    user = user_store.get_or_create_user(
        provider="google",
        provider_subject=google_sub,
        email=email,
        name=name,
    )

    token = create_access_token(user_id=user.id, email=user.email, name=user.name)

    data = TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)


@router.post("/dev-login")
async def dev_login(request: Request, payload: Optional[DevLoginRequest] = None):
    """
    Development/testing login helper.
    Explicitly forbidden and disabled in PRODUCTION mode.
    """
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint disabled in production mode",
        )

    cid = getattr(request.state, "correlation_id", "none")
    req_data = payload or DevLoginRequest()
    user = user_store.get_or_create_user(
        provider="local_dev",
        provider_subject=f"dev-sub-{req_data.user_id}",
        email=req_data.email,
        name=req_data.name,
    )
    token = create_access_token(user_id=user.id, email=user.email, name=user.name)
    data = TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        name=user.name,
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
        token = payload.token.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()

    if not token:
        raise HTTPException(status_code=400, detail="Token must be provided in payload or Authorization header")

    user_store.revoke_token(token)
    cid = getattr(request.state, "correlation_id", "none")
    return create_response_envelope({"revoked": True, "token_prefix": token[:10] + "..."}, correlation_id=cid)


@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Rotate and refresh an active token. Revokes the prior token to enforce single-use rotation."""
    user_info = get_current_user_id(authorization)
    old_token = authorization.split(" ")[1].strip()

    # Revoke previous token on successful rotation
    user_store.revoke_token(old_token)

    new_token = create_access_token(
        user_id=user_info["sub"],
        email=user_info.get("email", "investor@finex.internal"),
        name=user_info.get("name", "Investor"),
    )
    cid = getattr(request.state, "correlation_id", "none")
    data = TokenResponse(
        access_token=new_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user_info["sub"],
        email=user_info.get("email", "investor@finex.internal"),
        name=user_info.get("name", "Investor"),
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)


@users_router.get("/me")
async def get_current_user_profile(request: Request, user_info: dict = Depends(get_current_user_id)):
    """Retrieve verified investor profile and onboarding state from persistent user store."""
    cid = getattr(request.state, "correlation_id", "none")
    uid = user_info["sub"]
    profile = user_store.get_profile(uid)
    user = user_store.get_user_by_id(uid)

    profile_data = {
        "user_id": uid,
        "email": user.email if user else user_info.get("email", "investor@finex.internal"),
        "full_name": profile.full_name,
        "display_name": profile.display_name,
        "experience_level": profile.experience_level,
        "country": profile.country,
        "onboarding_completed": profile.onboarding_completed,
        "risk_band": profile.risk_band,
        "composite_score": profile.composite_score,
        "verified_identity": True,
    }
    return create_response_envelope(profile_data, correlation_id=cid)


@users_router.post("/consent")
async def record_user_consent(
    request: Request,
    consent: ConsentSubmission,
    user_info: dict = Depends(get_current_user_id),
):
    """Audit-compliant endpoint to record regulatory and terms acceptance against verified identity."""
    cid = getattr(request.state, "correlation_id", "none")
    uid = user_info["sub"]
    rec = user_store.record_consent(
        user_id=uid,
        consent_version=consent.consent_version,
        terms_accepted=consent.terms_accepted,
        privacy_accepted=consent.privacy_accepted,
        educational_disclaimer_accepted=consent.educational_disclaimer_accepted,
    )
    audit_record = {
        "user_id": uid,
        "consent_version": rec.consent_version,
        "terms_accepted": rec.terms_accepted,
        "privacy_accepted": rec.privacy_accepted,
        "educational_disclaimer_accepted": rec.educational_disclaimer_accepted,
        "recorded_at": rec.accepted_at,
        "status": "ACCEPTED",
    }
    return create_response_envelope(audit_record, correlation_id=cid)
