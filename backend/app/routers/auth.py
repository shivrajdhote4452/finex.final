"""Authentication, Identity Provider Verification, and User Profile Routers.

Task ID: CH-01, S2-API-01, S2-API-02
Enforces fail-closed authentication (HTTP 401 on missing/invalid/expired/revoked tokens),
real Google OAuth cryptographic verification (aud, iss, exp, sub),
and durable user profile and consent management.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.database import get_db
from backend.app.domain.user_store import user_store
from backend.app.services.email_service import email_service
from backend.app.services.password_service import (
    auth_rate_limiter,
    hash_password,
    validate_password_strength,
    verify_password,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])
users_router = APIRouter(prefix="/users", tags=["User Profile & Consent"])


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., description="Cryptographically signed Google OAuth ID token")


class SignupRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Account password (min 8 characters)")
    name: Optional[str] = Field("Investor", description="Full name or display name")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Account password")


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., description="Single-use email verification token")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="User email address")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Single-use password reset token")
    new_password: str = Field(..., description="New account password (min 8 characters)")


class SetPasswordRequest(BaseModel):
    new_password: str = Field(..., description="New account password (min 8 characters)")
    current_password: Optional[str] = Field(None, description="Current account password (required if changing)")


class ResendVerificationRequest(BaseModel):
    email: str = Field(..., description="User email address")


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


def create_access_token(user_id: str, email: str, name: str, provider: str = "google") -> str:
    """Generate a signed HS256 JWT access token with standard claims."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "provider": provider,
        "jti": str(uuid.uuid4()),
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def is_owner(user: object) -> bool:
    """Check if the user is the platform owner.

    Fails closed: returns False if OWNER_EMAIL is unset/empty or if user/email is missing.
    Owner privileges require a session established through verified Google OAuth.
    If provider metadata is present (on dict or user object), provider MUST equal 'google'.
    Matches case-insensitively with leading/trailing whitespace trimmed.
    Accepts a dict (JWT claims or profile dict), User, UserRecord, or email string.
    """
    settings = get_settings()
    owner_email = (getattr(settings, "OWNER_EMAIL", None) or "").strip().lower()
    if not owner_email:
        return False

    email: Optional[str] = None
    provider: Optional[str] = None

    if isinstance(user, dict):
        provider = user.get("provider")
        email = user.get("email")
    elif hasattr(user, "email"):
        provider = getattr(user, "provider", None)
        email = getattr(user, "email", None)
    elif isinstance(user, str):
        email = user

    if not email or not isinstance(email, str):
        return False

    # Non-Google session/provider can NEVER be owner
    if provider is not None and provider.strip().lower() != "google":
        return False

    return email.strip().lower() == owner_email


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    db: Optional[AsyncSession] = Depends(get_db),
) -> dict:
    """
    Fail-closed authentication dependency.
    Requires a valid, unrevoked Bearer JWT. Rejects missing, malformed,
    expired, or revoked tokens with HTTP 401 across restarts.
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

    is_revoked = await user_store.is_token_revoked_db(token, db=db)
    if is_revoked:
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


async def require_owner(current_user: dict = Depends(get_current_user_id)) -> dict:
    """FastAPI dependency to enforce owner-only access. Refuses non-owners with HTTP 403."""
    if current_user.get("provider") != "google" or not is_owner(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Sandbox controls and accounts are restricted to the platform owner.",
        )
    return current_user


@router.post("/google")
async def google_auth_callback(
    request: Request,
    payload: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with Google OAuth ID token.
    Validates Google signature, permitted audience, issuer, and expiration.
    Never passes audience=None as a production fallback.
    Maps verified Google subject to an internal user identity in PostgreSQL.
    """
    cid = getattr(request.state, "correlation_id", "none")
    raw_token = payload.id_token.strip()

    # Determine permitted audiences - accepts configured client ID and standard FinEx web client ID
    KNOWN_WEB_CLIENT_ID = "71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com"
    allowed_audiences = [KNOWN_WEB_CLIENT_ID]

    configured_aud = settings.GOOGLE_CLIENT_ID
    if configured_aud and configured_aud not in ["placeholder-google-client-id", "finex-dev-client-id"]:
        if configured_aud not in allowed_audiences:
            allowed_audiences.append(configured_aud)

    try:
        id_info = google_id_token.verify_oauth2_token(
            raw_token,
            google_requests.Request(),
            audience=allowed_audiences if len(allowed_audiences) > 1 else allowed_audiences[0],
        )
        iss = id_info.get("iss", "")
        if iss not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError(f"Untrusted token issuer: {iss}")

        google_sub = id_info["sub"]
        email = id_info.get("email") or f"{google_sub}@google.user"
        name = id_info.get("name") or "Investor"
        google_email_verified = bool(id_info.get("email_verified", False))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google ID token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    # Persist user in PostgreSQL using verified unique provider and subject
    try:
        user = await user_store.get_or_create_user_db(
            provider="google",
            provider_subject=google_sub,
            email=email,
            name=name,
            google_email_verified=google_email_verified,
            db=db,
        )
    except ValueError as e:
        if "already linked to a different Google account" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        raise

    token = create_access_token(user_id=user.id, email=user.email, name=user.name, provider="google")

    data = TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)


@router.post("/signup")
async def signup_with_email(
    request: Request,
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account with email and password.

    Validates password strength, hashes password with bcrypt, persists unverified user,
    and dispatches a single-use email verification link.
    """
    cid = getattr(request.state, "correlation_id", "none")
    clean_email = payload.email.strip().lower()

    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required.",
        )

    is_valid_pw, pw_err = validate_password_strength(payload.password)
    if not is_valid_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_err or "Password does not meet complexity requirements.",
        )

    existing_user = await user_store.get_user_by_email_db(clean_email, db=db)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in or reset your password.",
        )

    hashed = hash_password(payload.password)
    clean_name = payload.name.strip() if payload.name else "Investor"

    new_user = await user_store.create_email_user_db(
        email=clean_email,
        password_hash=hashed,
        name=clean_name,
        db=db,
    )

    # Generate single-use verification token valid for configured hours
    raw_token = await user_store.create_auth_token_db(
        user_id=new_user.id,
        token_type="email_verification",
        expires_in_minutes=settings.EMAIL_VERIFICATION_EXPIRE_HOURS * 60,
        db=db,
    )

    # Dispatch verification email
    delivery = await email_service.send_verification_email(
        to_email=clean_email,
        name=clean_name,
        raw_token=raw_token,
    )

    if delivery.get("delivered"):
        delivery_msg = "Account created successfully. Please check your email to verify your address."
    elif delivery.get("status") == "test_captured":
        delivery_msg = "Account created. Verification token captured in test buffer."
    else:
        delivery_msg = "Account created. Email delivery is currently unavailable; please contact an administrator."

    resp_data = {
        "created": True,
        "user_id": new_user.id,
        "email": clean_email,
        "message": delivery_msg,
        "delivery_status": delivery.get("status"),
    }
    return create_response_envelope(resp_data, correlation_id=cid)


@router.post("/verify-email")
async def verify_email_token(
    request: Request,
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify user's email address using single-use verification token."""
    cid = getattr(request.state, "correlation_id", "none")
    raw_token = payload.token.strip()

    user_id = await user_store.verify_and_consume_auth_token_db(
        raw_token=raw_token,
        token_type="email_verification",
        db=db,
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or previously used verification link. Please request a new one.",
        )

    await user_store.mark_email_verified_db(user_id=user_id, db=db)
    user = await user_store.get_user_by_id_db(user_id=user_id, db=db)

    resp_data = {
        "verified": True,
        "email": user.email if user else "",
        "message": "Email address successfully verified. You can now sign in.",
    }
    return create_response_envelope(resp_data, correlation_id=cid)


@router.post("/login")
async def login_with_email(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with verified email and password.

    Rate-limited per email and IP address to prevent brute-force and credential stuffing.
    Issues standard JWT access token on success.
    """
    cid = getattr(request.state, "correlation_id", "none")
    clean_email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"

    # Check brute-force rate limiter
    is_locked, retry_after = auth_rate_limiter.check_login_rate_limit(f"email:{clean_email}")
    if not is_locked:
        is_locked, retry_after = auth_rate_limiter.check_login_rate_limit(f"ip:{client_ip}")

    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please wait {retry_after} seconds before trying again.",
            headers={"Retry-After": str(retry_after)},
        )

    user = await user_store.get_user_by_email_db(clean_email, db=db)

    # Generic credential check (timing and presence safe)
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        auth_rate_limiter.record_login_failure(f"email:{clean_email}")
        auth_rate_limiter.record_login_failure(f"ip:{client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact support.",
        )

    # Require email verification before login
    if not user.email_verified and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address is not verified. Please check your inbox or request a new verification link.",
        )

    # Reset rate-limiting buckets upon successful login
    auth_rate_limiter.reset_login_failures(f"email:{clean_email}")
    auth_rate_limiter.reset_login_failures(f"ip:{client_ip}")

    profile = await user_store.get_profile_db(user.id, db=db)
    display_name = (
        (profile.display_name if profile and profile.display_name else None)
        or (profile.full_name if profile and profile.full_name else None)
        or clean_email.split("@")[0]
    )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        name=display_name,
        provider="local",
    )

    data = TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        name=display_name,
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset link.

    Rate-limited to prevent abuse. Always returns a generic safe response
    to prevent email enumeration attacks.
    """
    cid = getattr(request.state, "correlation_id", "none")
    clean_email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"

    is_limited, retry_after = auth_rate_limiter.check_and_record_forgot_request(f"forgot:{clean_email}")
    if not is_limited:
        is_limited, retry_after = auth_rate_limiter.check_and_record_forgot_request(f"ip:{client_ip}")

    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {retry_after} seconds before requesting another password reset.",
            headers={"Retry-After": str(retry_after)},
        )

    has_smtp = bool(settings.SMTP_HOST)
    is_test = email_service._is_test_mode()

    if not has_smtp and not is_test:
        resp_data = {
            "sent": False,
            "message": "Password reset via email is currently unavailable because transactional email is not configured. Please sign in with Google or contact support.",
            "delivery_status": "smtp_not_configured",
        }
        return create_response_envelope(resp_data, correlation_id=cid)

    user = await user_store.get_user_by_email_db(clean_email, db=db)
    if user and user.is_active:
        profile = await user_store.get_profile_db(user.id, db=db)
        display_name = profile.full_name if profile and profile.full_name else clean_email.split("@")[0]

        raw_token = await user_store.create_auth_token_db(
            user_id=user.id,
            token_type="password_reset",
            expires_in_minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES,
            db=db,
        )
        delivery = await email_service.send_password_reset_email(
            to_email=user.email,
            name=display_name,
            raw_token=raw_token,
        )
        if not delivery.get("delivered") and delivery.get("status") != "test_captured":
            logger.warning(
                "Password reset email for %s could not be delivered: status=%s",
                clean_email,
                delivery.get("status"),
            )
            resp_data = {
                "sent": False,
                "message": "Password reset email could not be delivered due to a mail server issue. Please try again later or contact support.",
                "delivery_status": delivery.get("status"),
            }
            return create_response_envelope(resp_data, correlation_id=cid)

    # Safe generic response regardless of whether account was found
    resp_data = {
        "sent": True,
        "message": "If an account exists for this email address, password reset instructions have been sent.",
        "delivery_status": "delivered" if (has_smtp or is_test) else "queued",
    }
    return create_response_envelope(resp_data, correlation_id=cid)


@router.post("/reset-password")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset account password using a single-use reset token."""
    cid = getattr(request.state, "correlation_id", "none")
    raw_token = payload.token.strip()

    is_valid_pw, pw_err = validate_password_strength(payload.new_password)
    if not is_valid_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_err or "Password does not meet complexity requirements.",
        )

    user_id = await user_store.verify_and_consume_auth_token_db(
        raw_token=raw_token,
        token_type="password_reset",
        db=db,
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or previously used password reset link. Please request a new one.",
        )

    hashed = hash_password(payload.new_password)
    await user_store.set_user_password_db(user_id=user_id, password_hash=hashed, db=db)

    resp_data = {
        "reset": True,
        "message": "Password has been successfully updated. You can now sign in with your new password.",
    }
    return create_response_envelope(resp_data, correlation_id=cid)


@router.post("/resend-verification")
async def resend_verification_email(
    request: Request,
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resend email verification link for an unverified account."""
    cid = getattr(request.state, "correlation_id", "none")
    clean_email = payload.email.strip().lower()

    has_smtp = bool(settings.SMTP_HOST)
    is_test = email_service._is_test_mode()

    if not has_smtp and not is_test:
        resp_data = {
            "sent": False,
            "message": "Email verification resend is currently unavailable because transactional email is not configured. Please sign in with Google or contact support.",
            "delivery_status": "smtp_not_configured",
        }
        return create_response_envelope(resp_data, correlation_id=cid)

    user = await user_store.get_user_by_email_db(clean_email, db=db)
    if user and not (user.email_verified or user.is_verified):
        profile = await user_store.get_profile_db(user.id, db=db)
        display_name = profile.full_name if profile and profile.full_name else "Investor"

        raw_token = await user_store.create_auth_token_db(
            user_id=user.id,
            token_type="email_verification",
            expires_in_minutes=settings.EMAIL_VERIFICATION_EXPIRE_HOURS * 60,
            db=db,
        )
        delivery = await email_service.send_verification_email(
            to_email=user.email,
            name=display_name,
            raw_token=raw_token,
        )
        if not delivery.get("delivered") and delivery.get("status") != "test_captured":
            logger.warning(
                "Verification resend email for %s could not be delivered: status=%s",
                clean_email,
                delivery.get("status"),
            )
            resp_data = {
                "sent": False,
                "message": "Verification email could not be delivered due to a mail server issue. Please try again later or contact support.",
                "delivery_status": delivery.get("status"),
            }
            return create_response_envelope(resp_data, correlation_id=cid)

    resp_data = {
        "sent": True,
        "message": "If this account is registered and unverified, a new verification link has been sent.",
        "delivery_status": "delivered" if (has_smtp or is_test) else "queued",
    }
    return create_response_envelope(resp_data, correlation_id=cid)


@router.post("/set-password")
async def set_account_password(
    request: Request,
    payload: SetPasswordRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Set or update account password for the currently authenticated user.

    Allows Google-authenticated users to establish password access to their account,
    or existing password users to update their credentials.
    """
    cid = getattr(request.state, "correlation_id", "none")
    user_id = current_user["sub"]

    is_valid_pw, pw_err = validate_password_strength(payload.new_password)
    if not is_valid_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_err or "Password does not meet complexity requirements.",
        )

    user = await user_store.get_user_by_id_db(user_id=user_id, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    # If user already has a password and logged in via local password, require current_password
    if user.password_hash and current_user.get("provider") != "google":
        if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

    hashed = hash_password(payload.new_password)
    await user_store.set_user_password_db(user_id=user_id, password_hash=hashed, db=db)

    resp_data = {
        "success": True,
        "message": "Account password set successfully. You can now sign in using your email and password.",
    }
    return create_response_envelope(resp_data, correlation_id=cid)


class RevokeRequest(BaseModel):
    token: Optional[str] = None


@router.post("/revoke")
async def revoke_access_token(
    request: Request,
    payload: Optional[RevokeRequest] = None,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an active JWT token persistently in PostgreSQL to deny subsequent requests across restarts."""
    token = None
    if payload and payload.token:
        token = payload.token.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()

    if not token:
        raise HTTPException(status_code=400, detail="Token must be provided in payload or Authorization header")

    await user_store.revoke_token_db(token, db=db)
    cid = getattr(request.state, "correlation_id", "none")
    return create_response_envelope({"revoked": True, "token_prefix": token[:10] + "..."}, correlation_id=cid)


@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Rotate and refresh an active token. Revokes the prior token persistently in PostgreSQL."""
    user_info = await get_current_user_id(authorization, db=db)
    old_token = authorization.split(" ")[1].strip()

    # Revoke previous token in PostgreSQL on successful rotation
    await user_store.revoke_token_db(old_token, db=db)

    new_token = create_access_token(
        user_id=user_info["sub"],
        email=user_info.get("email", "investor@finex.internal"),
        name=user_info.get("name", "Investor"),
        provider=user_info.get("provider", "google"),
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
async def get_current_user_profile(
    request: Request,
    user_info: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve verified investor profile and onboarding state from persistent PostgreSQL database."""
    cid = getattr(request.state, "correlation_id", "none")
    uid = user_info["sub"]
    profile = await user_store.get_profile_db(uid, db=db)
    user = await user_store.get_user_by_id_db(uid, db=db)

    resolved_email = user.email if user else user_info.get("email", "investor@finex.internal")

    user_provider = user.provider if user else user_info.get("provider")
    token_provider = user_info.get("provider")
    session_is_owner = (
        user_provider == "google"
        and token_provider == "google"
        and is_owner({"email": resolved_email, "provider": "google"})
    )

    profile_data = {
        "id": uid,
        "user_id": uid,
        "email": resolved_email,
        "full_name": profile.full_name,
        "display_name": profile.display_name,
        "experience_level": profile.experience_level,
        "country": profile.country,
        "onboarding_completed": profile.onboarding_completed,
        "risk_band": profile.risk_band,
        "composite_score": profile.composite_score,
        "verified_identity": True,
        "is_owner": session_is_owner,
        "has_password": bool(user and user.password_hash),
        "has_google": bool(user and (user.google_subject or user.provider == "google")),
        "email_verified": bool(user and (user.email_verified or user.is_verified)),
    }
    return create_response_envelope(profile_data, correlation_id=cid)


@users_router.post("/consent")
async def record_user_consent(
    request: Request,
    consent: ConsentSubmission,
    user_info: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Audit-compliant endpoint to record regulatory and terms acceptance against verified identity in PostgreSQL."""
    cid = getattr(request.state, "correlation_id", "none")
    uid = user_info["sub"]
    rec = await user_store.record_consent_db(
        user_id=uid,
        consent_version=consent.consent_version,
        terms_accepted=consent.terms_accepted,
        privacy_accepted=consent.privacy_accepted,
        educational_disclaimer_accepted=consent.educational_disclaimer_accepted,
        db=db,
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
