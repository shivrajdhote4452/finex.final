"""Financial Goal Projection Engine and Deterministic Calculations.

Task ID: S7-API-01
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Deterministic Future Value (FV) and Required Monthly Contribution formulas.
2. Versioned projection assumptions ('fv_compound_monthly_v1.0').
3. Goal CRUD operations and contribution ledger updates.
4. Zero LLM arithmetic: All numerical projections are computed deterministically.
"""

import math
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.database import AsyncSessionLocal
from backend.app.models.goals import FinancialGoal, GoalContribution
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# In-memory operational store for isolated testing/development baseline
_GOALS_STORE: Dict[str, Dict[str, Any]] = {}  # goal_id -> goal_dict
_CONTRIBUTIONS_STORE: Dict[str, List[Dict[str, Any]]] = {}  # goal_id -> list of contributions
_PROJECTIONS_STORE: Dict[str, List[Dict[str, Any]]] = {}  # goal_id -> list of projections


def _parse_uuid(val: Any) -> Optional[uuid.UUID]:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=128)
    category: str = Field(
        ...,
        description="'RETIREMENT', 'EMERGENCY_FUND', 'HOME_PURCHASE', 'EDUCATION', 'TRAVEL', 'WEALTH_CREATION', 'CUSTOM'",
    )
    target_amount: Decimal = Field(..., gt=0, description="Target corpus in INR")
    current_amount: Decimal = Field(Decimal("0.00"), ge=0, description="Initial corpus already saved")
    target_date: str = Field(..., description="Target completion date (YYYY-MM-DD)")
    assumed_annual_return_pct: Decimal = Field(Decimal("8.00"), ge=0, le=30, description="Assumed nominal annual CAGR")


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[Decimal] = None
    assumed_annual_return_pct: Optional[Decimal] = None
    status: Optional[str] = None


class ContributionCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Contribution amount in INR")
    contribution_date: str = Field(..., description="Date of deposit (YYYY-MM-DD)")
    notes: Optional[str] = None


class GoalProjectionResult(BaseModel):
    goal_id: str
    target_amount: float
    current_amount: float
    months_remaining: int
    assumed_annual_return_pct: float
    projected_future_value_zero_contributions: float
    required_monthly_savings: float
    progress_pct: float
    is_on_track: bool
    formula_version: str = "fv_compound_monthly_v1.0"
    assumptions: Dict[str, Any]
    statutory_disclaimer: str


STATUTORY_GOAL_DISCLAIMER = (
    "STATUTORY DISCLAIMER: Goal projections represent mathematical estimations based on stated constant compound rates. "
    "Market returns fluctuate over time and past performance does not guarantee future results. "
    "Projections do not account for taxes, inflation drag, or fund expense ratios unless explicitly specified."
)


def calculate_goal_projection(
    target_amount: Decimal,
    current_amount: Decimal,
    target_date_str: str,
    annual_return_pct: Decimal,
    reference_date_str: str = "2026-10-16",
    planned_monthly_contribution: Decimal = Decimal("0.00"),
) -> GoalProjectionResult:
    """Calculates deterministic future value and required monthly contribution."""
    ref_d = date.fromisoformat(reference_date_str)
    tgt_d = date.fromisoformat(target_date_str)

    if tgt_d <= ref_d:
        raise ValueError(f"Target date {target_date_str} must be in the future (after {reference_date_str}).")

    # Calculate exact months remaining
    total_days = (tgt_d - ref_d).days
    months_remaining = max(1, math.ceil(total_days / 30.4375))

    p = float(current_amount)
    fv_tgt = float(target_amount)
    annual_r = float(annual_return_pct) / 100.0
    r_monthly = annual_r / 12.0
    n = months_remaining

    # 1. Projected FV without any future additions
    if r_monthly > 0:
        fv_existing = p * ((1.0 + r_monthly) ** n)
    else:
        fv_existing = p

    # 2. Required Monthly Savings (PMT)
    # Target gap remaining = fv_tgt - fv_existing
    gap = fv_tgt - fv_existing
    if gap <= 0:
        required_pmt = 0.0
        is_on_track = True
    else:
        if r_monthly > 0:
            annuity_factor = (((1.0 + r_monthly) ** n) - 1.0) / r_monthly
            required_pmt = gap / annuity_factor
        else:
            required_pmt = gap / float(n)
        is_on_track = float(planned_monthly_contribution) >= required_pmt

    progress_pct = round((p / fv_tgt) * 100.0, 2) if fv_tgt > 0 else 0.0

    assumptions = {
        "reference_date": reference_date_str,
        "target_date": target_date_str,
        "months_remaining": months_remaining,
        "compounding_frequency": "MONTHLY",
        "assumed_annual_rate": float(annual_return_pct),
        "formula": "FV = P * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]",
    }

    return GoalProjectionResult(
        goal_id="temp",
        target_amount=round(fv_tgt, 2),
        current_amount=round(p, 2),
        months_remaining=months_remaining,
        assumed_annual_return_pct=float(annual_return_pct),
        projected_future_value_zero_contributions=round(fv_existing, 2),
        required_monthly_savings=round(max(0.0, required_pmt), 2),
        progress_pct=progress_pct,
        is_on_track=is_on_track,
        assumptions=assumptions,
        statutory_disclaimer=STATUTORY_GOAL_DISCLAIMER,
    )


class GoalEngine:
    """Manages user goals and computes deterministic projections."""

    def create_goal(self, user_id: str, payload: GoalCreate) -> Dict[str, Any]:
        # Validate projection first to confirm valid future date
        calculate_goal_projection(
            target_amount=payload.target_amount,
            current_amount=payload.current_amount,
            target_date_str=payload.target_date,
            annual_return_pct=payload.assumed_annual_return_pct,
        )

        goal_id = f"goal-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        goal = {
            "id": goal_id,
            "user_id": user_id,
            "title": payload.title,
            "category": payload.category,
            "target_amount": payload.target_amount,
            "current_amount": payload.current_amount,
            "currency": "INR",
            "target_date": payload.target_date,
            "assumed_annual_return_pct": payload.assumed_annual_return_pct,
            "status": "ACTIVE",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        _GOALS_STORE[goal_id] = goal
        return goal

    def get_user_goals(self, user_id: str) -> List[Dict[str, Any]]:
        user_goals = [g for g in _GOALS_STORE.values() if g["user_id"] == user_id]
        return sorted(user_goals, key=lambda x: x["target_date"])

    def get_goal_by_id(self, user_id: str, goal_id: str) -> Optional[Dict[str, Any]]:
        goal = _GOALS_STORE.get(goal_id)
        if not goal or goal["user_id"] != user_id:
            return None
        return goal

    def update_goal(self, user_id: str, goal_id: str, payload: GoalUpdate) -> Dict[str, Any]:
        goal = self.get_goal_by_id(user_id, goal_id)
        if not goal:
            raise KeyError(f"Goal {goal_id} not found or access denied.")

        if payload.title is not None:
            goal["title"] = payload.title
        if payload.target_amount is not None:
            goal["target_amount"] = payload.target_amount
        if payload.assumed_annual_return_pct is not None:
            goal["assumed_annual_return_pct"] = payload.assumed_annual_return_pct
        if payload.status is not None:
            goal["status"] = payload.status

        goal["updated_at"] = datetime.now(timezone.utc).isoformat()
        _GOALS_STORE[goal_id] = goal
        return goal

    def record_contribution(self, user_id: str, goal_id: str, payload: ContributionCreate) -> Dict[str, Any]:
        goal = self.get_goal_by_id(user_id, goal_id)
        if not goal:
            raise KeyError(f"Goal {goal_id} not found or access denied.")

        contrib_id = f"contrib-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        contrib = {
            "id": contrib_id,
            "goal_id": goal_id,
            "user_id": user_id,
            "amount": payload.amount,
            "contribution_date": payload.contribution_date,
            "notes": payload.notes,
            "created_at": now.isoformat(),
        }
        _CONTRIBUTIONS_STORE.setdefault(goal_id, []).append(contrib)

        # Update goal current amount
        goal["current_amount"] = goal["current_amount"] + payload.amount
        goal["updated_at"] = now.isoformat()
        _GOALS_STORE[goal_id] = goal

        return {
            "contribution": contrib,
            "updated_goal_balance": goal["current_amount"],
        }

    def get_goal_projection(self, user_id: str, goal_id: str) -> GoalProjectionResult:
        goal = self.get_goal_by_id(user_id, goal_id)
        if not goal:
            raise KeyError(f"Goal {goal_id} not found or access denied.")

        proj = calculate_goal_projection(
            target_amount=goal["target_amount"],
            current_amount=goal["current_amount"],
            target_date_str=goal["target_date"],
            annual_return_pct=goal["assumed_annual_return_pct"],
        )
        proj.goal_id = goal_id
        return proj

    async def create_goal_db(
        self,
        user_id: str,
        payload: GoalCreate,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Create and durably persist a user financial goal in PostgreSQL."""
        calculate_goal_projection(
            target_amount=payload.target_amount,
            current_amount=payload.current_amount,
            target_date_str=payload.target_date,
            annual_return_pct=payload.assumed_annual_return_pct,
        )
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            target_d = (
                date.fromisoformat(payload.target_date) if isinstance(payload.target_date, str) else payload.target_date
            )
            now = datetime.now(timezone.utc)
            goal_uuid = uuid.uuid4()
            goal_entity = FinancialGoal(
                id=goal_uuid,
                user_id=user_id,
                title=payload.title,
                category=payload.category,
                target_amount=Decimal(str(payload.target_amount)),
                current_amount=Decimal(str(payload.current_amount)),
                currency="INR",
                target_date=target_d,
                assumed_annual_return_pct=Decimal(str(payload.assumed_annual_return_pct)),
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
            session.add(goal_entity)
            if owns_session:
                await session.commit()
            else:
                await session.flush()

            goal_dict = {
                "id": str(goal_uuid),
                "user_id": user_id,
                "title": payload.title,
                "category": payload.category,
                "target_amount": float(payload.target_amount),
                "current_amount": float(payload.current_amount),
                "currency": "INR",
                "target_date": target_d.isoformat(),
                "assumed_annual_return_pct": float(payload.assumed_annual_return_pct),
                "status": "ACTIVE",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            _GOALS_STORE[str(goal_uuid)] = goal_dict
            return goal_dict
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def get_user_goals_db(
        self,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve all goals belonging to authenticated user from PostgreSQL."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            stmt = (
                select(FinancialGoal).where(FinancialGoal.user_id == user_id).order_by(FinancialGoal.target_date.asc())
            )
            res = await session.execute(stmt)
            goals = res.scalars().all()
            result = []
            for g in goals:
                d = {
                    "id": str(g.id),
                    "user_id": g.user_id,
                    "title": g.title,
                    "category": g.category,
                    "target_amount": float(g.target_amount),
                    "current_amount": float(g.current_amount),
                    "currency": g.currency,
                    "target_date": g.target_date.isoformat()
                    if hasattr(g.target_date, "isoformat")
                    else str(g.target_date),
                    "assumed_annual_return_pct": float(g.assumed_annual_return_pct),
                    "status": g.status,
                    "created_at": g.created_at.isoformat() if hasattr(g.created_at, "isoformat") else str(g.created_at),
                    "updated_at": g.updated_at.isoformat() if hasattr(g.updated_at, "isoformat") else str(g.updated_at),
                }
                result.append(d)
                _GOALS_STORE[str(g.id)] = d
            return result
        finally:
            if owns_session:
                await session.close()

    async def get_goal_by_id_db(
        self,
        user_id: str,
        goal_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve single goal by ID with user ownership check from PostgreSQL."""
        goal_uuid = _parse_uuid(goal_id)
        if not goal_uuid:
            goal = _GOALS_STORE.get(goal_id)
            if goal and goal["user_id"] == user_id:
                return goal
            return None

        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            stmt = select(FinancialGoal).where(
                FinancialGoal.id == goal_uuid,
                FinancialGoal.user_id == user_id,
            )
            res = await session.execute(stmt)
            g = res.scalar_one_or_none()
            if not g:
                return None
            d = {
                "id": str(g.id),
                "user_id": g.user_id,
                "title": g.title,
                "category": g.category,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "currency": g.currency,
                "target_date": g.target_date.isoformat() if hasattr(g.target_date, "isoformat") else str(g.target_date),
                "assumed_annual_return_pct": float(g.assumed_annual_return_pct),
                "status": g.status,
                "created_at": g.created_at.isoformat() if hasattr(g.created_at, "isoformat") else str(g.created_at),
                "updated_at": g.updated_at.isoformat() if hasattr(g.updated_at, "isoformat") else str(g.updated_at),
            }
            _GOALS_STORE[str(g.id)] = d
            return d
        finally:
            if owns_session:
                await session.close()

    async def update_goal_db(
        self,
        user_id: str,
        goal_id: str,
        payload: GoalUpdate,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Update goal parameters in PostgreSQL with row locking."""
        goal_uuid = _parse_uuid(goal_id)
        if not goal_uuid:
            return self.update_goal(user_id, goal_id, payload)

        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            stmt = (
                select(FinancialGoal)
                .where(
                    FinancialGoal.id == goal_uuid,
                    FinancialGoal.user_id == user_id,
                )
                .with_for_update()
            )
            res = await session.execute(stmt)
            g = res.scalar_one_or_none()
            if not g:
                raise KeyError(f"Goal {goal_id} not found or access denied.")

            if payload.title is not None:
                g.title = payload.title
            if payload.target_amount is not None:
                g.target_amount = Decimal(str(payload.target_amount))
            if payload.assumed_annual_return_pct is not None:
                g.assumed_annual_return_pct = Decimal(str(payload.assumed_annual_return_pct))
            if payload.status is not None:
                g.status = payload.status

            now = datetime.now(timezone.utc)
            g.updated_at = now
            if owns_session:
                await session.commit()
            else:
                await session.flush()

            d = {
                "id": str(g.id),
                "user_id": g.user_id,
                "title": g.title,
                "category": g.category,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "currency": g.currency,
                "target_date": g.target_date.isoformat() if hasattr(g.target_date, "isoformat") else str(g.target_date),
                "assumed_annual_return_pct": float(g.assumed_annual_return_pct),
                "status": g.status,
                "created_at": g.created_at.isoformat() if hasattr(g.created_at, "isoformat") else str(g.created_at),
                "updated_at": now.isoformat(),
            }
            _GOALS_STORE[str(g.id)] = d
            return d
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def record_contribution_db(
        self,
        user_id: str,
        goal_id: str,
        payload: ContributionCreate,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Record cash deposit towards goal in PostgreSQL with atomic balance update."""
        goal_uuid = _parse_uuid(goal_id)
        if not goal_uuid:
            return self.record_contribution(user_id, goal_id, payload)

        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            stmt = (
                select(FinancialGoal)
                .where(
                    FinancialGoal.id == goal_uuid,
                    FinancialGoal.user_id == user_id,
                )
                .with_for_update()
            )
            res = await session.execute(stmt)
            g = res.scalar_one_or_none()
            if not g:
                raise KeyError(f"Goal {goal_id} not found or access denied.")

            contrib_uuid = uuid.uuid4()
            now = datetime.now(timezone.utc)
            contrib_d = (
                date.fromisoformat(payload.contribution_date)
                if isinstance(payload.contribution_date, str)
                else payload.contribution_date
            )

            contrib_entity = GoalContribution(
                id=contrib_uuid,
                goal_id=g.id,
                user_id=user_id,
                amount=Decimal(str(payload.amount)),
                contribution_date=contrib_d,
                notes=payload.notes,
                created_at=now,
            )
            session.add(contrib_entity)

            g.current_amount = g.current_amount + Decimal(str(payload.amount))
            g.updated_at = now

            if owns_session:
                await session.commit()
            else:
                await session.flush()

            contrib_dict = {
                "id": str(contrib_uuid),
                "goal_id": str(g.id),
                "user_id": user_id,
                "amount": float(payload.amount),
                "contribution_date": contrib_d.isoformat(),
                "notes": payload.notes,
                "created_at": now.isoformat(),
            }
            _CONTRIBUTIONS_STORE.setdefault(str(g.id), []).append(contrib_dict)
            _GOALS_STORE[str(g.id)] = {
                "id": str(g.id),
                "user_id": g.user_id,
                "title": g.title,
                "category": g.category,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "currency": g.currency,
                "target_date": g.target_date.isoformat() if hasattr(g.target_date, "isoformat") else str(g.target_date),
                "assumed_annual_return_pct": float(g.assumed_annual_return_pct),
                "status": g.status,
                "created_at": g.created_at.isoformat() if hasattr(g.created_at, "isoformat") else str(g.created_at),
                "updated_at": now.isoformat(),
            }

            return {
                "contribution": contrib_dict,
                "updated_goal_balance": float(g.current_amount),
            }
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def get_goal_projection_db(
        self,
        user_id: str,
        goal_id: str,
        db: Optional[AsyncSession] = None,
    ) -> GoalProjectionResult:
        """Compute projection based on goal data retrieved from PostgreSQL."""
        goal = await self.get_goal_by_id_db(user_id, goal_id, db=db)
        if not goal:
            raise KeyError(f"Goal {goal_id} not found or access denied.")

        proj = calculate_goal_projection(
            target_amount=Decimal(str(goal["target_amount"])),
            current_amount=Decimal(str(goal["current_amount"])),
            target_date_str=goal["target_date"],
            annual_return_pct=Decimal(str(goal["assumed_annual_return_pct"])),
        )
        proj.goal_id = goal_id
        return proj
