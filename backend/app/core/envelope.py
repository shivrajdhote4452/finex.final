from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total matching items")
    total_pages: int = Field(..., ge=0, description="Total pages available")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")


class ResponseMeta(BaseModel):
    correlation_id: str = Field(..., description="Tracing UUID")
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp")
    version: str = Field("v1", description="API version")
    pagination: Optional[PaginationMeta] = Field(None, description="Optional pagination details")


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = Field(True, description="Always true for success responses")
    data: DataT = Field(..., description="Response payload")
    meta: ResponseMeta = Field(..., description="Response metadata")


def create_response_envelope(
    data: Any,
    correlation_id: str,
    pagination: Optional[PaginationMeta] = None,
) -> dict:
    """Helper to assemble a standardized success dictionary."""
    return {
        "success": True,
        "data": data,
        "meta": {
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "v1",
            "pagination": pagination.model_dump() if pagination else None,
        },
    }
