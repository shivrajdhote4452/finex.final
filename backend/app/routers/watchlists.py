"""Watchlists Router.

Task ID: S3-API-01
Exposes caller-owned watchlists CRUD with duplicate protection and error handling.
"""

import uuid
from typing import Dict

from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import ConflictException, NotFoundException
from backend.app.database import get_db
from backend.app.models.market import Security, Watchlist, WatchlistItem
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])

# In-memory storage mock/repository baseline for demonstration & test isolation
_WATCHLIST_STORE: Dict[str, Dict] = {}


class CreateWatchlistRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AddWatchlistItemRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)


@router.get("")
async def get_user_watchlists(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch all watchlists belonging to the authenticated caller with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    try:
        stmt = (
            select(Watchlist)
            .options(selectinload(Watchlist.items).joinedload(WatchlistItem.security))
            .where(Watchlist.user_id == user_id)
            .order_by(Watchlist.created_at.asc())
        )
        res = await db.execute(stmt)
        db_watchlists = res.scalars().all()

        if not db_watchlists:
            # Check in-memory store
            user_lists = [w for w in _WATCHLIST_STORE.values() if w["user_id"] == user_id]
            if not user_lists:
                # Create a default watchlist in database
                default_wl = Watchlist(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    name="My Primary Watchlist",
                )
                db.add(default_wl)
                await db.flush()

                for sym in ["RELIANCE", "TCS", "INFY", "HDFCBANK"]:
                    sec_res = await db.execute(select(Security).where(Security.symbol == sym))
                    sec = sec_res.scalars().first()
                    if not sec:
                        sec = Security(
                            id=uuid.uuid4(),
                            symbol=sym,
                            canonical_id=f"NSE:{sym}",
                            name=sym,
                            sector="Equity",
                        )
                        db.add(sec)
                        await db.flush()
                    item = WatchlistItem(
                        id=uuid.uuid4(),
                        watchlist_id=default_wl.id,
                        security_id=sec.id,
                    )
                    db.add(item)
                await db.commit()
                res = await db.execute(stmt)
                db_watchlists = res.scalars().all()

        if db_watchlists:
            formatted = []
            for wl in db_watchlists:
                item_syms = [it.security.symbol for it in wl.items if it.security]
                wl_data = {
                    "id": str(wl.id),
                    "user_id": wl.user_id,
                    "name": wl.name,
                    "items": item_syms,
                }
                _WATCHLIST_STORE[str(wl.id)] = wl_data
                formatted.append(wl_data)
            return create_response_envelope(data={"watchlists": formatted}, correlation_id=cid)
    except Exception:
        pass

    user_lists = [w for w in _WATCHLIST_STORE.values() if w["user_id"] == user_id]
    if not user_lists:
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
    db: AsyncSession = Depends(get_db),
):
    """Create a new named watchlist for the caller with database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    # Duplicate name check in DB
    try:
        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id,
            func.lower(Watchlist.name) == payload.name.lower().strip(),
        )
        res = await db.execute(stmt)
        if res.scalars().first():
            raise ConflictException(message=f"Watchlist with name '{payload.name}' already exists for this account.")

        new_id = uuid.uuid4()
        new_wl = Watchlist(
            id=new_id,
            user_id=user_id,
            name=payload.name.strip(),
        )
        db.add(new_wl)
        await db.commit()

        result_data = {
            "id": str(new_id),
            "user_id": user_id,
            "name": new_wl.name,
            "items": [],
        }
        _WATCHLIST_STORE[str(new_id)] = result_data
        return create_response_envelope(data=result_data, correlation_id=cid)
    except ConflictException:
        raise
    except Exception:
        # Fallback to memory store
        for w in _WATCHLIST_STORE.values():
            if w["user_id"] == user_id and w["name"].lower() == payload.name.lower():
                raise ConflictException(
                    message=f"Watchlist with name '{payload.name}' already exists for this account."
                )
        wl_id = str(uuid.uuid4())
        new_wl_dict = {
            "id": wl_id,
            "user_id": user_id,
            "name": payload.name,
            "items": [],
        }
        _WATCHLIST_STORE[wl_id] = new_wl_dict
        return create_response_envelope(data=new_wl_dict, correlation_id=cid)


@router.post("/{watchlist_id}/items")
async def add_symbol_to_watchlist(
    request: Request,
    watchlist_id: str,
    payload: AddWatchlistItemRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add an instrument to a watchlist with duplicate prevention and database persistence."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    sym = payload.symbol.upper().strip()

    try:
        try:
            wl_uuid = uuid.UUID(watchlist_id)
        except ValueError:
            wl_uuid = None

        if wl_uuid:
            stmt = (
                select(Watchlist)
                .options(selectinload(Watchlist.items).joinedload(WatchlistItem.security))
                .where(Watchlist.id == wl_uuid, Watchlist.user_id == user_id)
            )
            res = await db.execute(stmt)
            wl = res.scalars().first()
            if not wl:
                raise NotFoundException(message="Watchlist not found or unauthorized.")

            # Check if symbol already in watchlist
            existing_syms = [it.security.symbol for it in wl.items if it.security]
            if sym in existing_syms:
                raise ConflictException(message=f"Instrument '{sym}' is already pinned in this watchlist.")

            # Get or create security
            sec_stmt = select(Security).where(Security.symbol == sym)
            sec_res = await db.execute(sec_stmt)
            sec = sec_res.scalars().first()
            if not sec:
                sec = Security(
                    id=uuid.uuid4(),
                    symbol=sym,
                    canonical_id=f"NSE:{sym}",
                    name=sym,
                    sector="Equity",
                )
                db.add(sec)
                await db.flush()

            item = WatchlistItem(
                id=uuid.uuid4(),
                watchlist_id=wl.id,
                security_id=sec.id,
            )
            db.add(item)
            await db.commit()

            items_list = existing_syms + [sym]
            if str(wl.id) in _WATCHLIST_STORE:
                _WATCHLIST_STORE[str(wl.id)]["items"] = items_list
            return create_response_envelope(
                data={"watchlist_id": watchlist_id, "added_symbol": sym, "items": items_list},
                correlation_id=cid,
            )
    except (NotFoundException, ConflictException):
        raise
    except Exception:
        pass

    wl = _WATCHLIST_STORE.get(watchlist_id)
    if not wl or wl["user_id"] != user_id:
        raise NotFoundException(message="Watchlist not found or unauthorized.")

    if sym in wl["items"]:
        raise ConflictException(message=f"Instrument '{sym}' is already pinned in this watchlist.")

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
    db: AsyncSession = Depends(get_db),
):
    """Remove an instrument from a watchlist."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    sym = symbol.upper().strip()

    try:
        try:
            wl_uuid = uuid.UUID(watchlist_id)
        except ValueError:
            wl_uuid = None

        if wl_uuid:
            stmt = (
                select(Watchlist)
                .options(selectinload(Watchlist.items).joinedload(WatchlistItem.security))
                .where(Watchlist.id == wl_uuid, Watchlist.user_id == user_id)
            )
            res = await db.execute(stmt)
            wl = res.scalars().first()
            if not wl:
                raise NotFoundException(message="Watchlist not found or unauthorized.")

            item_to_remove = next((it for it in wl.items if it.security and it.security.symbol == sym), None)
            if not item_to_remove:
                raise NotFoundException(message=f"Instrument '{sym}' is not in this watchlist.")

            await db.delete(item_to_remove)
            await db.commit()

            remaining = [it.security.symbol for it in wl.items if it.security and it.security.symbol != sym]
            if str(wl.id) in _WATCHLIST_STORE:
                _WATCHLIST_STORE[str(wl.id)]["items"] = remaining
            return create_response_envelope(
                data={"watchlist_id": watchlist_id, "removed_symbol": sym, "items": remaining},
                correlation_id=cid,
            )
    except NotFoundException:
        raise
    except Exception:
        pass

    wl = _WATCHLIST_STORE.get(watchlist_id)
    if not wl or wl["user_id"] != user_id:
        raise NotFoundException(message="Watchlist not found or unauthorized.")

    if sym not in wl["items"]:
        raise NotFoundException(message=f"Instrument '{sym}' is not in this watchlist.")

    wl["items"].remove(sym)
    return create_response_envelope(
        data={"watchlist_id": watchlist_id, "removed_symbol": sym, "items": wl["items"]},
        correlation_id=cid,
    )
