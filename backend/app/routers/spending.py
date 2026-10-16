"""Spending Analytics & CSV Ingestion API Router.

Task ID: S7-API-02
Author: Shivraj Dhote
Date: 16 October 2026

Exposes:
- POST /spending/upload: Ingest CSV file with row validation, PII masking, and duplicate detection
- GET /spending/transactions: Retrieve masked transactions list
- PATCH /spending/transactions/{transaction_id}/category: Correct transaction category
- GET /spending/summary: Monthly spending rollup and category breakdown
"""

from typing import Optional

from backend.app.core.envelope import create_response_envelope
from backend.app.domain.spending_service import SpendingService
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/spending", tags=["Spending Analytics & Ingestion"])
spending_service = SpendingService()


class CategoryUpdateRequest(BaseModel):
    category_id: str = Field(..., description="Target category ID (e.g. 'FOOD_DINING', 'TRAVEL')")


class CsvTextUploadRequest(BaseModel):
    file_name: str
    csv_content: str


@router.post("/upload")
async def upload_transactions_csv(
    request: Request,
    payload: CsvTextUploadRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Ingest bank statement CSV with PII masking and categorization."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        res = spending_service.ingest_csv(
            user_id=user_id,
            file_name=payload.file_name,
            csv_content=payload.csv_content,
        )
        return create_response_envelope(data=res, correlation_id=cid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/transactions")
async def list_transactions(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category ID"),
    year_month: Optional[str] = Query(None, description="Filter by YYYY-MM (e.g. 2026-10)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_id),
):
    """List masked transactions with category filter."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    res = spending_service.list_transactions(
        user_id=user_id,
        category=category,
        year_month=year_month,
        limit=limit,
        offset=offset,
    )
    return create_response_envelope(data=res, correlation_id=cid)


@router.patch("/transactions/{transaction_id}/category")
async def update_transaction_category(
    transaction_id: str,
    request: Request,
    payload: CategoryUpdateRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Update or correct category for a transaction."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        updated = spending_service.update_transaction_category(
            user_id=user_id,
            transaction_id=transaction_id,
            new_category=payload.category_id,
        )
        return create_response_envelope(data=updated, correlation_id=cid)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found or access denied.",
        )


@router.get("/summary")
async def get_monthly_spending_summary(
    request: Request,
    year_month: str = Query("2026-10", description="Target month in YYYY-MM"),
    current_user: dict = Depends(get_current_user_id),
):
    """Retrieve monthly spending roll-up by category."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    summary = spending_service.get_monthly_summary(user_id=user_id, year_month=year_month)
    return create_response_envelope(data=summary.model_dump(mode="json"), correlation_id=cid)
