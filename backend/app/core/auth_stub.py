from typing import Optional

from backend.app.core.errors import UnauthorizedException
from fastapi import Header
from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    user_id: str = Field(..., description="Application user UUID")
    email: str = Field(..., description="User email address")
    role: str = Field("user", description="Authorization role")


async def get_current_user_stub(
    authorization: Optional[str] = Header(None, description="Bearer <token> header"),
) -> AuthenticatedUser:
    """
    Isolated authentication stub for Sprint 1 tests and contract verification.
    NEVER used as production identity (reserved for Sprint 2 S2-API-01).
    Valid mock token format: 'Bearer test-user-token' or 'Bearer valid-user-<id>'
    """
    if not authorization:
        raise UnauthorizedException(message="Missing Authorization header", code="MISSING_TOKEN")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException(
            message="Invalid Authorization format. Expected 'Bearer <token>'",
            code="INVALID_TOKEN_FORMAT",
        )

    token = parts[1]
    if token == "invalid-token" or token == "expired-token":
        raise UnauthorizedException(message="Token is expired or invalid", code="TOKEN_EXPIRED")

    if token.startswith("valid-user-"):
        uid = token.replace("valid-user-", "")
        return AuthenticatedUser(user_id=uid, email=f"user-{uid}@example.com")

    if token == "test-user-token":
        return AuthenticatedUser(
            user_id="11111111-2222-3333-4444-555555555555",
            email="developer@finex.local",
            role="developer",
        )

    raise UnauthorizedException(message="Unrecognized authentication token", code="UNAUTHORIZED")
