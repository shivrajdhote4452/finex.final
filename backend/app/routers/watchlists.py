"""Watchlists Router.

Task ID: S3-API-01
Exposes caller-owned watchlists CRUD with duplicate protection and error handling.
"""

import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import ConflictException, NotFoundException
from backend.app.routers.auth import get_current_user_id

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])

# In-memory storage mock/repository baseline for demonstration & test isolation
_WATCHLIST_STORE: Dict[str, Dict] = {}


class CreateWatchlistRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AddWatchlistItemRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)


@router.get("")
async def get_user_watchlists(
    request: Request, current_user: dict = Depends(get_current_user_id)
):
    """Fetch all watchlists belonging to the authenticated caller."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    user_lists = [w for w in _WATCHLIST_STORE.values() if w["user_id"] == user_id]
    if not user_lists:
        # Create a default watchlist if none exists
        default_id = str(uuid.uuid4())
        default_wl = {
            "id": default_id,
            "user_id": user_id,
            "name": "My Primary Watchlist",
            "items": ["RELIANCE", "TCS", "INFY", "HDFCBANK"],
        }
        _WATCHLIST_STORE[default_id] = default_wl
        user_lists = [default_wl]

    return create_response_envelope(data={"watchlists": user_lists}, correlation_id=cid)


@router.post("")
async def create_user_watchlist(
    request: Request,
    payload: CreateWatchlistRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Create a new named watchlist for the caller."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    # Duplicate name check
    for w in _WATCHLIST_STORE.values():
        if w["user_id"] == user_id and w["name"].lower() == payload.name.lower():
            raise ConflictException(
                message=f"Watchlist with name '{payload.name}' already exists for this account."
            )

    wl_id = str(uuid.uuid4())
    new_wl = {
        "id": wl_id,
        "user_id": user_id,
        "name": payload.name,
        "items": [],
    }
    _WATCHLIST_STORE[wl_id] = new_wl

    return create_response_envelope(data=new_wl, correlation_id=cid)


@router.post("/{watchlist_id}/items")
async def add_symbol_to_watchlist(
    request: Request,
    watchlist_id: str,
    payload: AddWatchlistItemRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Add an instrument to a watchlist with duplicate prevention."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    wl = _WATCHLIST_STORE.get(watchlist_id)
    if not wl or wl["user_id"] != user_id:
        raise NotFoundException(message="Watchlist not found or unauthorized.")

    sym = payload.symbol.upper().strip()
    if sym in wl["items"]:
        raise ConflictException(
            message=f"Instrument '{sym}' is already pinned in this watchlist."
        )

    wl["items"].append(sym)
    return create_response_envelope(
        data={"watchlist_id": watchlist_id, "added_symbol": sym, "items": wl["items"]},
        correlation_id=cid,
    )


@router.delete("/{watchlist_id}/items/{symbol}")
async def remove_symbol_from_watchlist(
    request: Request,
    watchlist_id: str,
    symbol: str,
    current_user: dict = Depends(get_current_user_id),
):
    """Remove an instrument from a watchlist."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    wl = _WATCHLIST_STORE.get(watchlist_id)
    if not wl or wl["user_id"] != user_id:
        raise NotFoundException(message="Watchlist not found or unauthorized.")

    sym = symbol.upper().strip()
    if sym not in wl["items"]:
        raise NotFoundException(
            message=f"Instrument '{sym}' is not in this watchlist."
        )

    wl["items"].remove(sym)
    return create_response_envelope(
        data={"watchlist_id": watchlist_id, "removed_symbol": sym, "items": wl["items"]},
        correlation_id=cid,
    )
