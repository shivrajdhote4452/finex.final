from decimal import Decimal

from backend.app.core.auth_stub import AuthenticatedUser, get_current_user_stub
from backend.app.core.envelope import create_response_envelope
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sample", tags=["Sample Verification Endpoints"])


class SampleCalculationRequest(BaseModel):
    quantity: Decimal = Field(..., gt=0, description="Holding quantity (must be > 0)")
    price: Decimal = Field(..., ge=0, description="Share price (must be >= 0)")
    trigger_error: bool = Field(False, description="Flag to deliberately trigger 500 server error")


class SampleCalculationResponse(BaseModel):
    market_value: Decimal
    currency: str = "INR"


@router.post(
    "/calculate",
    summary="Sample Calculation with Schema Validation",
    description="Calculates market value = quantity * price. Validates 200, 422, and 500 payloads.",
)
async def calculate_sample(request: Request, body: SampleCalculationRequest):
    if body.trigger_error:
        raise RuntimeError("Deliberate internal server error for envelope verification")

    cid = getattr(request.state, "correlation_id", "none")
    result = SampleCalculationResponse(
        market_value=body.quantity * body.price,
        currency="INR",
    )
    return create_response_envelope(result.model_dump(), correlation_id=cid)


@router.get(
    "/protected",
    summary="Sample Protected Route",
    description="Requires valid Bearer token stub. Demonstrates auth dependency protection.",
)
async def get_protected_data(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user_stub),
):
    cid = getattr(request.state, "correlation_id", "none")
    return create_response_envelope(
        {
            "message": f"Hello {current_user.email}, you are authorized.",
            "user_id": current_user.user_id,
            "role": current_user.role,
        },
        correlation_id=cid,
    )
