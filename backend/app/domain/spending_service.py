"""Spending Analytics, CSV Normalization, Masking, and Categorization Service.

Task ID: S7-API-02
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. CSV parsing, validation, and quarantine handling.
2. PII / account masking before operational storage or AI usage.
3. Rule-based categorization with review flags and confidence scoring.
4. Monthly spending roll-up calculation (total debits, credits, savings rate %, category breakdown).
5. Duplicate transaction detection via SHA-256 fingerprinting.
"""

import csv
import hashlib
import io
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.database import AsyncSessionLocal
from backend.app.models.spending import (
    Transaction,
    TransactionCategory,
    TransactionPreview,
    TransactionUpload,
)
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# In-memory operational store for isolated testing/development baseline
_UPLOADS_STORE: Dict[str, Dict[str, Any]] = {}  # upload_id -> upload_dict
_TRANSACTIONS_STORE: Dict[str, List[Dict[str, Any]]] = {}  # user_id -> list of transactions
_PREVIEWS_STORE: Dict[str, Dict[str, Any]] = {}  # preview_id -> preview_dict


def _parse_year_month_bounds(year_month: str) -> Tuple[date, date]:
    """Parse YYYY-MM into start_date (inclusive) and next_month_date (exclusive) for portable filtering."""
    try:
        parts = year_month.strip().split("-")
        year = int(parts[0])
        month = int(parts[1])
        start_date = date(year, month, 1)
        if month == 12:
            next_month_date = date(year + 1, 1, 1)
        else:
            next_month_date = date(year, month + 1, 1)
        return start_date, next_month_date
    except Exception:
        now = datetime.now(timezone.utc).date()
        start_date = date(now.year, now.month, 1)
        next_month = date(now.year + 1, 1, 1) if now.month == 12 else date(now.year, now.month + 1, 1)
        return start_date, next_month


def _parse_uuid(val: Any) -> Optional[uuid.UUID]:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None


DEFAULT_CATEGORIES = [
    {
        "id": "FOOD_DINING",
        "name": "Food & Dining",
        "description": "Restaurants, takeout, cafes, food delivery",
        "is_essential": False,
    },
    {
        "id": "GROCERIES",
        "name": "Groceries",
        "description": "Supermarkets, daily essentials, grocery deliveries",
        "is_essential": True,
    },
    {
        "id": "UTILITIES",
        "name": "Utilities & Bills",
        "description": "Electricity, water, mobile bills, internet",
        "is_essential": True,
    },
    {
        "id": "HOUSING",
        "name": "Housing & Rent",
        "description": "Monthly apartment rent, maintenance charges",
        "is_essential": True,
    },
    {
        "id": "TRAVEL",
        "name": "Travel & Fuel",
        "description": "Cabs, fuel, flights, train tickets",
        "is_essential": False,
    },
    {
        "id": "SHOPPING",
        "name": "Shopping & Retail",
        "description": "Clothing, electronics, online shopping",
        "is_essential": False,
    },
    {
        "id": "HEALTHCARE",
        "name": "Healthcare & Medical",
        "description": "Pharmacies, clinic visits, hospital expenses",
        "is_essential": True,
    },
    {
        "id": "INVESTMENTS",
        "name": "Investments & Mutual Funds",
        "description": "SIPs, stock purchases, mutual fund investments",
        "is_essential": False,
    },
    {
        "id": "INCOME",
        "name": "Income & Salary",
        "description": "Salary credits, interest, dividend receipts",
        "is_essential": False,
    },
    {
        "id": "OTHER",
        "name": "Other Discretionary",
        "description": "Miscellaneous non-categorized transactions",
        "is_essential": False,
    },
    {
        "id": "UNASSIGNED",
        "name": "Unassigned",
        "description": "Transactions awaiting categorization",
        "is_essential": False,
    },
]


async def ensure_transaction_categories(session: AsyncSession) -> None:
    """Ensure core master categories exist in PostgreSQL transaction_categories table."""
    for cat in DEFAULT_CATEGORIES:
        stmt = select(TransactionCategory).where(TransactionCategory.id == cat["id"])
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            cat_obj = TransactionCategory(
                id=cat["id"],
                name=cat["name"],
                description=cat["description"],
                is_essential=cat["is_essential"],
                created_at=datetime.now(timezone.utc),
            )
            session.add(cat_obj)
    await session.flush()


async def ensure_category_exists(session: AsyncSession, cat_id: str) -> None:
    """Ensure specific category exists before inserting a transaction foreign key."""
    stmt = select(TransactionCategory).where(TransactionCategory.id == cat_id)
    res = await session.execute(stmt)
    if not res.scalar_one_or_none():
        cat_obj = TransactionCategory(
            id=cat_id,
            name=cat_id.replace("_", " ").title(),
            description="Auto-registered transaction category",
            is_essential=False,
            created_at=datetime.now(timezone.utc),
        )
        session.add(cat_obj)
        await session.flush()


# Keyword matching dictionary for deterministic categorization
CATEGORIZATION_RULES: List[Tuple[List[str], str, Decimal]] = [
    (["SWIGGY", "ZOMATO", "MCDONALDS", "STARBUCKS", "RESTAURANT", "CAFE", "DOMINOS"], "FOOD_DINING", Decimal("0.95")),
    (["BIGBASKET", "BLINKIT", "ZEPTO", "DMART", "SUPERMARKET", "GROCERY", "MORE RETAIL"], "GROCERIES", Decimal("0.95")),
    (["BESCOM", "AIRTEL", "JIO", "ELECTRICITY", "BROADBAND", "TNEB", "BILLPAY", "WATER"], "UTILITIES", Decimal("0.92")),
    (["RENT", "NOBROKER", "SOCIETY", "MAINTENANCE", "HOUSING"], "HOUSING", Decimal("0.95")),
    (["UBER", "OLA", "PETROL", "HPCL", "BPCL", "INDIGO", "IRCTC", "FUEL", "RAPIDO"], "TRAVEL", Decimal("0.92")),
    (["AMAZON", "FLIPKART", "MYNTRA", "ZARA", "UNIQLO", "SHOPPING", "RETAIL"], "SHOPPING", Decimal("0.90")),
    (["APOLLO", "PHARMEASY", "MEDPLUS", "HOSPITAL", "CLINIC", "PHARMACY", "DOCTOR"], "HEALTHCARE", Decimal("0.95")),
    (
        ["ZERODHA", "GROWW", "MUTUAL FUND", "SIP", "NIPPON", "HDFC AMC", "COIN", "INVEST"],
        "INVESTMENTS",
        Decimal("0.95"),
    ),
    (["SALARY", "DIVIDEND", "INTEREST", "CREDIT PAYROLL", "INCOME"], "INCOME", Decimal("0.98")),
]


def mask_sensitive_narrative(raw_desc: str) -> str:
    """Masks 10-16 digit account numbers, cards, or phone numbers to preserve user privacy."""
    # Mask 12-16 digit card or reference numbers
    masked = re.sub(r"\b\d{12,16}\b", "****", raw_desc)
    # Mask 10-digit phone / UPI phone patterns
    masked = re.sub(r"\b\d{10}\b", "****", masked)
    # Mask UPI handles with numbers (e.g. user9876543210@upi)
    masked = re.sub(r"\b[A-Za-z0-9._%+-]+@upi\b", "****@upi", masked, flags=re.IGNORECASE)
    return masked.strip()


def categorize_transaction(description: str, tx_type: str) -> Tuple[str, Decimal, str]:
    """Applies rule-based taxonomy to determine category, confidence, and method."""
    desc_upper = description.upper()

    if tx_type == "CREDIT" and any(k in desc_upper for k in ["SALARY", "INTEREST", "REFUND", "PAYROLL"]):
        return "INCOME", Decimal("0.98"), "RULE"

    for keywords, category, conf in CATEGORIZATION_RULES:
        if any(kw in desc_upper for kw in keywords):
            return category, conf, "RULE"

    return "OTHER", Decimal("0.60"), "AI_FALLBACK"


class TransactionItem(BaseModel):
    id: str
    transaction_date: str
    amount: float
    transaction_type: str
    masked_description: str
    category_id: str
    categorization_method: str
    confidence_score: float
    is_reviewed: bool


class MonthlySpendingSummaryResult(BaseModel):
    user_id: str
    year_month: str
    total_debit: float
    total_credit: float
    net_savings: float
    savings_rate_pct: float
    transaction_count: int
    category_breakdown: Dict[str, float]


class SpendingService:
    """Processes bank CSV uploads, manages transactions, and computes monthly summaries."""

    def ingest_csv(
        self,
        user_id: str,
        file_name: str,
        csv_content: str,
    ) -> Dict[str, Any]:
        file_hash = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()

        # Check duplicate upload for this user
        if file_hash in [u["file_hash_sha256"] for u in _UPLOADS_STORE.values() if u["user_id"] == user_id]:
            raise ValueError(f"Duplicate file upload detected. File '{file_name}' has already been processed.")

        upload_id = f"upl-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        if not reader.fieldnames:
            raise ValueError("Invalid CSV: Empty file or missing header row.")

        # Normalize header keys
        headers = {h.lower().strip(): h for h in reader.fieldnames}
        date_key = next((headers[k] for k in ["date", "transaction_date", "tx_date"] if k in headers), None)
        amt_key = next((headers[k] for k in ["amount", "tx_amount", "value"] if k in headers), None)
        desc_key = next((headers[k] for k in ["description", "narration", "remarks", "details"] if k in headers), None)
        type_key = next((headers[k] for k in ["type", "transaction_type", "dr_cr"] if k in headers), None)

        if not (date_key and amt_key and desc_key):
            raise ValueError(
                f"Missing required CSV columns. Found {list(reader.fieldnames)}. Required: Date, Amount, Description."
            )

        accepted_txs = []
        quarantined = []
        user_txs = _TRANSACTIONS_STORE.setdefault(user_id, [])

        for row_idx, row in enumerate(reader, start=1):
            raw_d = row.get(date_key, "").strip()
            raw_amt = row.get(amt_key, "").strip().replace(",", "")
            raw_desc = row.get(desc_key, "").strip()
            raw_type = (row.get(type_key, "") if type_key else "DEBIT").strip().upper()

            if not raw_type or raw_type in ("DR", "EXPENSE", "DEBIT"):
                tx_type = "DEBIT"
            elif raw_type in ("CR", "INCOME", "CREDIT"):
                tx_type = "CREDIT"
            else:
                tx_type = "DEBIT"

            try:
                # Validate date format (YYYY-MM-DD or DD/MM/YYYY)
                parsed_d = None
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        parsed_d = datetime.strptime(raw_d, fmt).date()
                        break
                    except ValueError:
                        continue
                if not parsed_d:
                    raise ValueError(f"Invalid date format: '{raw_d}'")

                amt = Decimal(raw_amt)
                if amt <= 0:
                    raise ValueError(f"Amount must be positive: {amt}")

                # Mask PII in description
                masked_desc = mask_sensitive_narrative(raw_desc)
                cat, conf, method = categorize_transaction(masked_desc, tx_type)

                # Dedupe hash (date + amount + description)
                tx_hash = hashlib.sha256(f"{parsed_d}:{amt}:{masked_desc}".encode("utf-8")).hexdigest()

                # Check if this exact transaction already exists
                if any(t["dedupe_hash"] == tx_hash for t in user_txs):
                    # Duplicate row; skip
                    continue

                tx_id = f"tx-{uuid.uuid4().hex[:12]}"
                tx_record = {
                    "id": tx_id,
                    "upload_id": upload_id,
                    "user_id": user_id,
                    "transaction_date": parsed_d.isoformat(),
                    "amount": amt,
                    "transaction_type": tx_type,
                    "masked_description": masked_desc,
                    "category_id": cat,
                    "categorization_method": method,
                    "confidence_score": conf,
                    "is_reviewed": conf >= Decimal("0.90"),
                    "dedupe_hash": tx_hash,
                    "created_at": now.isoformat(),
                }
                accepted_txs.append(tx_record)
                user_txs.append(tx_record)

            except Exception as e:
                quarantined.append({"row_number": row_idx, "error": str(e), "raw_row": row})

        upload_meta = {
            "id": upload_id,
            "user_id": user_id,
            "file_name": file_name,
            "file_hash_sha256": file_hash,
            "total_rows": len(accepted_txs) + len(quarantined),
            "accepted_rows": len(accepted_txs),
            "quarantined_rows": len(quarantined),
            "status": "COMMITTED" if accepted_txs else "REJECTED",
            "created_at": now.isoformat(),
        }
        _UPLOADS_STORE[upload_id] = upload_meta

        return {
            "upload": upload_meta,
            "accepted_count": len(accepted_txs),
            "quarantined_count": len(quarantined),
            "quarantined_errors": quarantined[:5],
        }

    def list_transactions(
        self,
        user_id: str,
        category: Optional[str] = None,
        year_month: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        txs = _TRANSACTIONS_STORE.get(user_id, [])
        filtered = txs
        if category:
            filtered = [t for t in filtered if t["category_id"] == category]
        if year_month:
            filtered = [t for t in filtered if t["transaction_date"].startswith(year_month)]

        filtered = sorted(filtered, key=lambda x: x["transaction_date"], reverse=True)
        paginated = filtered[offset : offset + limit]

        out = [
            TransactionItem(
                id=t["id"],
                transaction_date=t["transaction_date"],
                amount=float(t["amount"]),
                transaction_type=t["transaction_type"],
                masked_description=t["masked_description"],
                category_id=t["category_id"],
                categorization_method=t["categorization_method"],
                confidence_score=float(t["confidence_score"]),
                is_reviewed=t["is_reviewed"],
            )
            for t in paginated
        ]

        return {
            "total": len(filtered),
            "transactions": [o.model_dump(mode="json") for o in out],
        }

    def update_transaction_category(self, user_id: str, transaction_id: str, new_category: str) -> Dict[str, Any]:
        txs = _TRANSACTIONS_STORE.get(user_id, [])
        tx = next((t for t in txs if t["id"] == transaction_id), None)
        if not tx:
            raise KeyError(f"Transaction {transaction_id} not found or access denied.")

        tx["category_id"] = new_category
        tx["categorization_method"] = "USER_CORRECTED"
        tx["confidence_score"] = Decimal("1.00")
        tx["is_reviewed"] = True
        return tx

    def get_monthly_summary(self, user_id: str, year_month: str = "2026-10") -> MonthlySpendingSummaryResult:
        txs = _TRANSACTIONS_STORE.get(user_id, [])
        month_txs = [t for t in txs if t["transaction_date"].startswith(year_month)]

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        category_breakdown: Dict[str, Decimal] = {}

        for t in month_txs:
            amt = t["amount"]
            if t["transaction_type"] == "DEBIT":
                total_debit += amt
                cat = t["category_id"]
                category_breakdown[cat] = category_breakdown.get(cat, Decimal("0.00")) + amt
            else:
                total_credit += amt

        net_savings = total_credit - total_debit
        savings_rate = (
            round((net_savings / total_credit * Decimal("100.0")), 2) if total_credit > 0 else Decimal("0.00")
        )

        return MonthlySpendingSummaryResult(
            user_id=user_id,
            year_month=year_month,
            total_debit=float(total_debit),
            total_credit=float(total_credit),
            net_savings=float(net_savings),
            savings_rate_pct=float(savings_rate),
            transaction_count=len(month_txs),
            category_breakdown={
                k: float(v) for k, v in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
            },
        )

    def preview_csv(
        self,
        user_id: str,
        file_name: str,
        csv_content: str,
    ) -> Dict[str, Any]:
        """CH-09: Parse bank statement CSV into an isolated preview without committing records."""
        file_hash = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()
        is_duplicate_file = file_hash in [
            u["file_hash_sha256"] for u in _UPLOADS_STORE.values() if u["user_id"] == user_id
        ]
        if is_duplicate_file:
            raise ValueError(f"Duplicate file upload detected. File '{file_name}' has already been processed.")

        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        if not reader.fieldnames:
            raise ValueError("Invalid CSV: Empty file or missing header row.")

        headers = {h.lower().strip(): h for h in reader.fieldnames}
        date_key = next((headers[k] for k in ["date", "transaction_date", "tx_date"] if k in headers), None)
        amt_key = next((headers[k] for k in ["amount", "tx_amount", "value"] if k in headers), None)
        desc_key = next((headers[k] for k in ["description", "narration", "remarks", "details"] if k in headers), None)
        type_key = next((headers[k] for k in ["type", "transaction_type", "dr_cr"] if k in headers), None)

        if not (date_key and amt_key and desc_key):
            raise ValueError(
                f"Missing required CSV columns. Found {list(reader.fieldnames)}. Required: Date, Amount, Description."
            )

        valid_rows = []
        duplicate_rows = []
        invalid_rows = []
        user_txs = _TRANSACTIONS_STORE.get(user_id, [])
        now = datetime.now(timezone.utc)

        seen_in_file = set()
        for row_idx, row in enumerate(reader, start=1):
            raw_d = row.get(date_key, "").strip()
            raw_amt = row.get(amt_key, "").strip().replace(",", "")
            raw_desc = row.get(desc_key, "").strip()
            raw_type = (row.get(type_key, "") if type_key else "DEBIT").strip().upper()

            tx_type = "CREDIT" if raw_type in ("CR", "INCOME", "CREDIT") else "DEBIT"

            try:
                parsed_d = None
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        parsed_d = datetime.strptime(raw_d, fmt).date()
                        break
                    except ValueError:
                        continue
                if not parsed_d:
                    raise ValueError(f"Invalid date format: '{raw_d}'")

                amt = Decimal(raw_amt)
                if amt <= 0:
                    raise ValueError(f"Amount must be positive: {amt}")

                masked_desc = mask_sensitive_narrative(raw_desc)
                cat, conf, method = categorize_transaction(masked_desc, tx_type)
                tx_hash = hashlib.sha256(f"{parsed_d}:{amt}:{masked_desc}".encode("utf-8")).hexdigest()

                if tx_hash in seen_in_file:
                    duplicate_rows.append(
                        {"row_number": row_idx, "reason": "Duplicate row within file", "raw_row": row}
                    )
                    continue

                if any(t["dedupe_hash"] == tx_hash for t in user_txs):
                    duplicate_rows.append(
                        {"row_number": row_idx, "reason": "Already exists in transactions", "raw_row": row}
                    )
                    continue

                seen_in_file.add(tx_hash)

                valid_rows.append(
                    {
                        "row_index": row_idx,
                        "date": parsed_d.isoformat(),
                        "amount": float(amt),
                        "type": tx_type,
                        "masked_description": masked_desc,
                        "category": cat,
                        "confidence": float(conf),
                        "method": method,
                        "dedupe_hash": tx_hash,
                    }
                )
            except Exception as e:
                invalid_rows.append({"row_number": row_idx, "error": str(e), "raw_row": row})

        preview_id = f"prev-{uuid.uuid4().hex[:12]}"
        preview_meta = {
            "id": preview_id,
            "user_id": user_id,
            "file_name": file_name,
            "file_hash_sha256": file_hash,
            "total_rows": len(valid_rows) + len(duplicate_rows) + len(invalid_rows),
            "valid_rows": valid_rows,
            "duplicate_rows": duplicate_rows,
            "invalid_rows": invalid_rows,
            "status": "PENDING_REVIEW",
            "created_at": now.isoformat(),
            "committed_upload_id": None,
        }
        _PREVIEWS_STORE[preview_id] = preview_meta

        return {
            "preview_id": preview_id,
            "file_name": file_name,
            "total_rows": preview_meta["total_rows"],
            "valid_count": len(valid_rows),
            "duplicate_count": len(duplicate_rows),
            "invalid_count": len(invalid_rows),
            "valid_rows": valid_rows[:50],
            "invalid_rows": invalid_rows[:10],
            "status": "PENDING_REVIEW",
        }

    def commit_csv(
        self,
        user_id: str,
        preview_id: str,
        accepted_indices: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """CH-09: Atomically commit accepted preview rows to active ledger."""
        if preview_id not in _PREVIEWS_STORE:
            raise KeyError(f"Preview session '{preview_id}' not found or expired.")

        preview = _PREVIEWS_STORE[preview_id]
        if preview["user_id"] != user_id:
            raise KeyError("Access denied to this preview session.")

        if preview["status"] == "COMMITTED":
            # Idempotent replay: return already-committed metadata
            prior_upload_id = preview["committed_upload_id"]
            prior_upload = _UPLOADS_STORE.get(prior_upload_id, {})
            return {
                "upload_id": prior_upload_id,
                "accepted_count": prior_upload.get("accepted_rows", len(preview["valid_rows"])),
                "duplicate_count": len(preview.get("duplicate_rows", [])),
                "quarantined_count": prior_upload.get("quarantined_rows", len(preview.get("invalid_rows", []))),
                "status": "COMMITTED",
                "replayed": True,
            }

        # Check if another preview of the exact same file was already committed for this user
        file_hash = preview["file_hash_sha256"]
        prior_committed = next(
            (u for u in _UPLOADS_STORE.values() if u["user_id"] == user_id and u["file_hash_sha256"] == file_hash),
            None,
        )
        if prior_committed:
            preview["status"] = "COMMITTED"
            preview["committed_upload_id"] = prior_committed["id"]
            return {
                "upload_id": prior_committed["id"],
                "accepted_count": prior_committed.get("accepted_rows", 0),
                "duplicate_count": len(preview.get("valid_rows", [])),
                "quarantined_count": prior_committed.get("quarantined_rows", 0),
                "status": "COMMITTED",
                "replayed": True,
            }

        now = datetime.now(timezone.utc)
        upload_id = f"upl-{uuid.uuid4().hex[:12]}"
        user_txs = _TRANSACTIONS_STORE.setdefault(user_id, [])

        rows_to_commit = preview["valid_rows"]
        if accepted_indices is not None:
            idx_set = set(accepted_indices)
            rows_to_commit = [r for r in rows_to_commit if r["row_index"] in idx_set]

        # Re-check duplicates inside commit transaction
        existing_hashes = {t["dedupe_hash"] for t in user_txs}
        seen_commit_hashes = set()
        committed_txs = []
        commit_skipped_duplicates = 0

        for r in rows_to_commit:
            h = r["dedupe_hash"]
            if h in existing_hashes or h in seen_commit_hashes:
                commit_skipped_duplicates += 1
                continue
            seen_commit_hashes.add(h)
            existing_hashes.add(h)

            tx_id = f"tx-{uuid.uuid4().hex[:12]}"
            tx_record = {
                "id": tx_id,
                "upload_id": upload_id,
                "user_id": user_id,
                "transaction_date": r["date"],
                "amount": Decimal(str(r["amount"])),
                "transaction_type": r["type"],
                "masked_description": r["masked_description"],
                "category_id": r["category"],
                "categorization_method": r["method"],
                "confidence_score": Decimal(str(r["confidence"])),
                "is_reviewed": r["confidence"] >= 0.90,
                "dedupe_hash": h,
                "created_at": now.isoformat(),
            }
            committed_txs.append(tx_record)
            user_txs.append(tx_record)

        total_duplicates = len(preview.get("duplicate_rows", [])) + commit_skipped_duplicates
        upload_meta = {
            "id": upload_id,
            "user_id": user_id,
            "file_name": preview["file_name"],
            "file_hash_sha256": file_hash,
            "total_rows": preview["total_rows"],
            "accepted_rows": len(committed_txs),
            "duplicate_rows": total_duplicates,
            "quarantined_rows": len(preview["invalid_rows"]),
            "status": "COMMITTED",
            "created_at": now.isoformat(),
        }
        _UPLOADS_STORE[upload_id] = upload_meta

        preview["status"] = "COMMITTED"
        preview["committed_upload_id"] = upload_id

        return {
            "upload_id": upload_id,
            "accepted_count": len(committed_txs),
            "duplicate_count": total_duplicates,
            "quarantined_count": len(preview["invalid_rows"]),
            "status": "COMMITTED",
            "replayed": False,
        }

    def add_manual_transaction(
        self,
        user_id: str,
        transaction_date: str,
        amount: Decimal,
        description: str,
        transaction_type: str = "DEBIT",
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """CH-09: Support durable manual transaction entry with PII masking and categorization."""
        now = datetime.now(timezone.utc)
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        masked_desc = mask_sensitive_narrative(description)
        cat = category_id
        method = "MANUAL_USER"
        conf = Decimal("1.00")

        if not cat:
            cat, conf, method = categorize_transaction(masked_desc, transaction_type)

        tx_hash = hashlib.sha256(f"{transaction_date}:{amount}:{masked_desc}".encode("utf-8")).hexdigest()
        tx_id = f"tx-{uuid.uuid4().hex[:12]}"
        tx_record = {
            "id": tx_id,
            "upload_id": "manual-entry",
            "user_id": user_id,
            "transaction_date": transaction_date,
            "amount": amount,
            "transaction_type": transaction_type,
            "masked_description": masked_desc,
            "category_id": cat,
            "categorization_method": method,
            "confidence_score": conf,
            "is_reviewed": True,
            "dedupe_hash": tx_hash,
            "created_at": now.isoformat(),
        }

        user_txs = _TRANSACTIONS_STORE.setdefault(user_id, [])
        user_txs.append(tx_record)
        return tx_record

    async def preview_csv_db(
        self,
        user_id: str,
        file_name: str,
        csv_content: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Parse bank statement CSV into preview with PostgreSQL duplicate upload and hash verification."""
        file_hash = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            # Check duplicate upload in PostgreSQL
            stmt_upload = select(TransactionUpload).where(
                TransactionUpload.user_id == user_id,
                TransactionUpload.file_hash_sha256 == file_hash,
                TransactionUpload.status == "COMMITTED",
            )
            res_upload = await session.execute(stmt_upload)
            if res_upload.scalar_one_or_none():
                raise ValueError(f"Duplicate file upload detected. File '{file_name}' has already been processed.")

            # Also check in-memory store
            if any(
                u["file_hash_sha256"] == file_hash
                for u in _UPLOADS_STORE.values()
                if u["user_id"] == user_id and u.get("status") == "COMMITTED"
            ):
                raise ValueError(f"Duplicate file upload detected. File '{file_name}' has already been processed.")

            reader = csv.DictReader(io.StringIO(csv_content.strip()))
            if not reader.fieldnames:
                raise ValueError("Invalid CSV: Empty file or missing header row.")

            headers = {h.lower().strip(): h for h in reader.fieldnames}
            date_key = next((headers[k] for k in ["date", "transaction_date", "tx_date"] if k in headers), None)
            amt_key = next((headers[k] for k in ["amount", "tx_amount", "value"] if k in headers), None)
            desc_key = next(
                (headers[k] for k in ["description", "narration", "remarks", "details"] if k in headers), None
            )
            type_key = next((headers[k] for k in ["type", "transaction_type", "dr_cr"] if k in headers), None)

            if not (date_key and amt_key and desc_key):
                raise ValueError(
                    f"Missing required CSV columns. Found {list(reader.fieldnames)}. Required: Date, Amount, Description."
                )

            # Query existing transaction hashes for this user from PostgreSQL
            stmt_tx = select(Transaction.dedupe_hash).where(Transaction.user_id == user_id)
            res_tx = await session.execute(stmt_tx)
            existing_db_hashes = set(res_tx.scalars().all())

            # Combine with in-memory hashes
            for t in _TRANSACTIONS_STORE.get(user_id, []):
                existing_db_hashes.add(t["dedupe_hash"])

            valid_rows = []
            duplicate_rows = []
            invalid_rows = []
            seen_in_file: Set[str] = set()
            now = datetime.now(timezone.utc)

            for row_idx, row in enumerate(reader, start=1):
                raw_d = row.get(date_key, "").strip()
                raw_amt = row.get(amt_key, "").strip().replace(",", "")
                raw_desc = row.get(desc_key, "").strip()
                raw_type = (row.get(type_key, "") if type_key else "DEBIT").strip().upper()
                tx_type = "CREDIT" if raw_type in ("CR", "INCOME", "CREDIT") else "DEBIT"

                try:
                    parsed_d = None
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            parsed_d = datetime.strptime(raw_d, fmt).date()
                            break
                        except ValueError:
                            continue
                    if not parsed_d:
                        raise ValueError(f"Invalid date format: '{raw_d}'")

                    amt = Decimal(raw_amt)
                    if amt <= 0:
                        raise ValueError(f"Amount must be positive: {amt}")

                    masked_desc = mask_sensitive_narrative(raw_desc)
                    cat, conf, method = categorize_transaction(masked_desc, tx_type)
                    tx_hash = hashlib.sha256(f"{parsed_d}:{amt}:{masked_desc}".encode("utf-8")).hexdigest()

                    if tx_hash in seen_in_file:
                        duplicate_rows.append(
                            {"row_number": row_idx, "reason": "Duplicate row within file", "raw_row": row}
                        )
                        continue

                    if tx_hash in existing_db_hashes:
                        duplicate_rows.append(
                            {"row_number": row_idx, "reason": "Already exists in transactions", "raw_row": row}
                        )
                        continue

                    seen_in_file.add(tx_hash)
                    valid_rows.append(
                        {
                            "row_index": row_idx,
                            "date": parsed_d.isoformat(),
                            "amount": float(amt),
                            "type": tx_type,
                            "masked_description": masked_desc,
                            "category": cat,
                            "confidence": float(conf),
                            "method": method,
                            "dedupe_hash": tx_hash,
                        }
                    )
                except Exception as e:
                    invalid_rows.append({"row_number": row_idx, "error": str(e), "raw_row": row})

            preview_id = f"prev-{uuid.uuid4().hex[:12]}"
            expires_at = now + timedelta(hours=24)
            db_preview = TransactionPreview(
                id=preview_id,
                user_id=user_id,
                file_name=file_name,
                file_hash_sha256=file_hash,
                total_rows=len(valid_rows) + len(duplicate_rows) + len(invalid_rows),
                valid_rows=valid_rows,
                duplicate_rows=duplicate_rows,
                invalid_rows=invalid_rows,
                status="PENDING_REVIEW",
                committed_upload_id=None,
                created_at=now,
                expires_at=expires_at,
            )
            session.add(db_preview)
            if owns_session:
                await session.commit()
            else:
                await session.flush()

            preview_meta = {
                "id": preview_id,
                "user_id": user_id,
                "file_name": file_name,
                "file_hash_sha256": file_hash,
                "total_rows": len(valid_rows) + len(duplicate_rows) + len(invalid_rows),
                "valid_rows": valid_rows,
                "duplicate_rows": duplicate_rows,
                "invalid_rows": invalid_rows,
                "status": "PENDING_REVIEW",
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "committed_upload_id": None,
            }
            _PREVIEWS_STORE[preview_id] = preview_meta

            return {
                "preview_id": preview_id,
                "file_name": file_name,
                "total_rows": preview_meta["total_rows"],
                "valid_count": len(valid_rows),
                "duplicate_count": len(duplicate_rows),
                "invalid_count": len(invalid_rows),
                "valid_rows": valid_rows[:50],
                "invalid_rows": invalid_rows[:10],
                "status": "PENDING_REVIEW",
            }
        finally:
            if owns_session:
                await session.close()

    async def commit_csv_db(
        self,
        user_id: str,
        preview_id: str,
        accepted_indices: Optional[List[int]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Atomically commit accepted preview rows to PostgreSQL ledger."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            now = datetime.now(timezone.utc)
            # 1. Fetch preview from DB with row lock or fallback to store
            stmt_prev = select(TransactionPreview).where(TransactionPreview.id == preview_id).with_for_update()
            res_prev = await session.execute(stmt_prev)
            db_preview = res_prev.scalar_one_or_none()

            preview: Dict[str, Any]
            if db_preview is not None:
                if db_preview.user_id != user_id:
                    raise KeyError("Access denied to this preview session.")
                exp_at = db_preview.expires_at
                if exp_at is not None:
                    if exp_at.tzinfo is None:
                        exp_at = exp_at.replace(tzinfo=timezone.utc)
                    else:
                        exp_at = exp_at.astimezone(timezone.utc)
                    if exp_at < now:
                        raise ValueError(f"Preview session '{preview_id}' not found or expired.")
                if db_preview.status == "COMMITTED":
                    prior_upload_id = db_preview.committed_upload_id
                    return {
                        "upload_id": prior_upload_id,
                        "accepted_count": len(db_preview.valid_rows or []),
                        "duplicate_count": len(db_preview.duplicate_rows or []),
                        "quarantined_count": len(db_preview.invalid_rows or []),
                        "status": "COMMITTED",
                        "replayed": True,
                    }
                preview = {
                    "id": db_preview.id,
                    "user_id": db_preview.user_id,
                    "file_name": db_preview.file_name,
                    "file_hash_sha256": db_preview.file_hash_sha256,
                    "total_rows": db_preview.total_rows,
                    "valid_rows": db_preview.valid_rows or [],
                    "duplicate_rows": db_preview.duplicate_rows or [],
                    "invalid_rows": db_preview.invalid_rows or [],
                    "status": db_preview.status,
                    "committed_upload_id": db_preview.committed_upload_id,
                }
            elif preview_id in _PREVIEWS_STORE:
                preview = _PREVIEWS_STORE[preview_id]
                if preview["user_id"] != user_id:
                    raise KeyError("Access denied to this preview session.")
                if "expires_at" in preview and preview["expires_at"]:
                    exp_dt = datetime.fromisoformat(preview["expires_at"])
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    else:
                        exp_dt = exp_dt.astimezone(timezone.utc)
                    if exp_dt < now:
                        raise ValueError(f"Preview session '{preview_id}' not found or expired.")
                if preview["status"] == "COMMITTED":
                    prior_upload_id = preview["committed_upload_id"]
                    return {
                        "upload_id": prior_upload_id,
                        "accepted_count": len(preview.get("valid_rows", [])),
                        "duplicate_count": len(preview.get("duplicate_rows", [])),
                        "quarantined_count": len(preview.get("invalid_rows", [])),
                        "status": "COMMITTED",
                        "replayed": True,
                    }
            else:
                raise KeyError(f"Preview session '{preview_id}' not found or expired.")

            file_hash = preview["file_hash_sha256"]
            # Check if another preview of the exact same file was already committed in PostgreSQL
            stmt_prior = select(TransactionUpload).where(
                TransactionUpload.user_id == user_id,
                TransactionUpload.file_hash_sha256 == file_hash,
                TransactionUpload.status == "COMMITTED",
            )
            res_prior = await session.execute(stmt_prior)
            prior_committed = res_prior.scalar_one_or_none()
            if prior_committed:
                if db_preview is not None:
                    db_preview.status = "COMMITTED"
                    db_preview.committed_upload_id = str(prior_committed.id)
                if preview_id in _PREVIEWS_STORE:
                    _PREVIEWS_STORE[preview_id]["status"] = "COMMITTED"
                    _PREVIEWS_STORE[preview_id]["committed_upload_id"] = str(prior_committed.id)
                if owns_session:
                    await session.commit()
                else:
                    await session.flush()
                return {
                    "upload_id": str(prior_committed.id),
                    "accepted_count": prior_committed.accepted_rows,
                    "duplicate_count": len(preview.get("valid_rows", [])),
                    "quarantined_count": prior_committed.quarantined_rows,
                    "status": "COMMITTED",
                    "replayed": True,
                }

            # Seed core master categories
            await ensure_transaction_categories(session)

            upload_uuid = uuid.uuid4()
            rows_to_commit = preview["valid_rows"]
            if accepted_indices is not None:
                idx_set = set(accepted_indices)
                rows_to_commit = [r for r in rows_to_commit if r["row_index"] in idx_set]

            # Query existing dedupe hashes in PostgreSQL
            stmt_hashes = select(Transaction.dedupe_hash).where(Transaction.user_id == user_id)
            res_hashes = await session.execute(stmt_hashes)
            existing_hashes = set(res_hashes.scalars().all())

            seen_commit_hashes: Set[str] = set()
            committed_tx_records = []
            commit_skipped_duplicates = 0

            for r in rows_to_commit:
                h = r["dedupe_hash"]
                if h in existing_hashes or h in seen_commit_hashes:
                    commit_skipped_duplicates += 1
                    continue
                seen_commit_hashes.add(h)
                existing_hashes.add(h)

                cat_id = r["category"]
                await ensure_category_exists(session, cat_id)

                tx_uuid = uuid.uuid4()
                tx_d = date.fromisoformat(r["date"])
                amt_dec = Decimal(str(r["amount"]))
                conf_dec = Decimal(str(r["confidence"]))

                tx_entity = Transaction(
                    id=tx_uuid,
                    upload_id=upload_uuid,
                    user_id=user_id,
                    transaction_date=tx_d,
                    amount=amt_dec,
                    transaction_type=r["type"],
                    masked_description=r["masked_description"],
                    category_id=cat_id,
                    categorization_method=r["method"],
                    confidence_score=conf_dec,
                    is_reviewed=conf_dec >= Decimal("0.90"),
                    dedupe_hash=h,
                    created_at=now,
                )
                session.add(tx_entity)

                tx_dict = {
                    "id": str(tx_uuid),
                    "upload_id": str(upload_uuid),
                    "user_id": user_id,
                    "transaction_date": r["date"],
                    "amount": amt_dec,
                    "transaction_type": r["type"],
                    "masked_description": r["masked_description"],
                    "category_id": cat_id,
                    "categorization_method": r["method"],
                    "confidence_score": conf_dec,
                    "is_reviewed": conf_dec >= Decimal("0.90"),
                    "dedupe_hash": h,
                    "created_at": now.isoformat(),
                }
                committed_tx_records.append(tx_dict)

            total_duplicates = len(preview.get("duplicate_rows", [])) + commit_skipped_duplicates
            upload_entity = TransactionUpload(
                id=upload_uuid,
                user_id=user_id,
                file_name=preview["file_name"],
                file_hash_sha256=file_hash,
                total_rows=preview["total_rows"],
                accepted_rows=len(committed_tx_records),
                quarantined_rows=len(preview["invalid_rows"]),
                status="COMMITTED",
                created_at=now,
            )
            session.add(upload_entity)

            if db_preview is not None:
                db_preview.status = "COMMITTED"
                db_preview.committed_upload_id = str(upload_uuid)

            if owns_session:
                await session.commit()
            else:
                await session.flush()

            upload_meta = {
                "id": str(upload_uuid),
                "user_id": user_id,
                "file_name": preview["file_name"],
                "file_hash_sha256": file_hash,
                "total_rows": preview["total_rows"],
                "accepted_rows": len(committed_tx_records),
                "duplicate_rows": total_duplicates,
                "quarantined_rows": len(preview["invalid_rows"]),
                "status": "COMMITTED",
                "created_at": now.isoformat(),
            }
            _UPLOADS_STORE[str(upload_uuid)] = upload_meta
            _TRANSACTIONS_STORE.setdefault(user_id, []).extend(committed_tx_records)

            if preview_id in _PREVIEWS_STORE:
                _PREVIEWS_STORE[preview_id]["status"] = "COMMITTED"
                _PREVIEWS_STORE[preview_id]["committed_upload_id"] = str(upload_uuid)

            return {
                "upload_id": str(upload_uuid),
                "accepted_count": len(committed_tx_records),
                "duplicate_count": total_duplicates,
                "quarantined_count": len(preview["invalid_rows"]),
                "status": "COMMITTED",
                "replayed": False,
            }
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def ingest_csv_db(
        self,
        user_id: str,
        file_name: str,
        csv_content: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Ingest CSV file directly into PostgreSQL via atomic preview + commit."""
        preview_res = await self.preview_csv_db(user_id, file_name, csv_content, db=db)
        commit_res = await self.commit_csv_db(user_id, preview_res["preview_id"], db=db)
        upload_meta = _UPLOADS_STORE.get(commit_res["upload_id"], {})
        return {
            "upload": upload_meta,
            "accepted_count": commit_res["accepted_count"],
            "quarantined_count": commit_res["quarantined_count"],
            "quarantined_errors": preview_res.get("invalid_rows", [])[:5],
        }

    async def list_transactions_db(
        self,
        user_id: str,
        category: Optional[str] = None,
        year_month: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """List transactions from PostgreSQL with user isolation and filtering."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            filters = [Transaction.user_id == user_id]
            if category:
                filters.append(Transaction.category_id == category)
            if year_month:
                start_date, next_month_date = _parse_year_month_bounds(year_month)
                filters.append(Transaction.transaction_date >= start_date)
                filters.append(Transaction.transaction_date < next_month_date)

            stmt_count = select(func.count(Transaction.id)).where(and_(*filters))
            res_count = await session.execute(stmt_count)
            total = res_count.scalar() or 0

            stmt = (
                select(Transaction)
                .where(and_(*filters))
                .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            res = await session.execute(stmt)
            txs = res.scalars().all()

            out = [
                TransactionItem(
                    id=str(t.id),
                    transaction_date=t.transaction_date.isoformat()
                    if hasattr(t.transaction_date, "isoformat")
                    else str(t.transaction_date),
                    amount=float(t.amount),
                    transaction_type=t.transaction_type,
                    masked_description=t.masked_description,
                    category_id=t.category_id,
                    categorization_method=t.categorization_method,
                    confidence_score=float(t.confidence_score),
                    is_reviewed=t.is_reviewed,
                )
                for t in txs
            ]

            return {
                "total": total,
                "transactions": [o.model_dump(mode="json") for o in out],
            }
        finally:
            if owns_session:
                await session.close()

    async def update_transaction_category_db(
        self,
        user_id: str,
        transaction_id: str,
        new_category: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Update transaction category in PostgreSQL with user ownership verification."""
        tx_uuid = _parse_uuid(transaction_id)
        if not tx_uuid:
            # Fallback to in-memory store
            return self.update_transaction_category(user_id, transaction_id, new_category)

        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            stmt = (
                select(Transaction)
                .where(
                    Transaction.id == tx_uuid,
                    Transaction.user_id == user_id,
                )
                .with_for_update()
            )
            res = await session.execute(stmt)
            tx = res.scalar_one_or_none()
            if not tx:
                raise KeyError(f"Transaction {transaction_id} not found or access denied.")

            await ensure_category_exists(session, new_category)
            tx.category_id = new_category
            tx.categorization_method = "USER_CORRECTED"
            tx.confidence_score = Decimal("1.00")
            tx.is_reviewed = True

            if owns_session:
                await session.commit()
            else:
                await session.flush()

            tx_dict = {
                "id": str(tx.id),
                "upload_id": str(tx.upload_id) if tx.upload_id else "manual-entry",
                "user_id": tx.user_id,
                "transaction_date": tx.transaction_date.isoformat()
                if hasattr(tx.transaction_date, "isoformat")
                else str(tx.transaction_date),
                "amount": tx.amount,
                "transaction_type": tx.transaction_type,
                "masked_description": tx.masked_description,
                "category_id": new_category,
                "categorization_method": "USER_CORRECTED",
                "confidence_score": Decimal("1.00"),
                "is_reviewed": True,
                "dedupe_hash": tx.dedupe_hash,
                "created_at": tx.created_at.isoformat() if hasattr(tx.created_at, "isoformat") else "",
            }
            # Keep in-memory store synchronized
            user_txs = _TRANSACTIONS_STORE.get(user_id, [])
            for mem_t in user_txs:
                if mem_t.get("id") == str(tx.id):
                    mem_t["category_id"] = new_category
                    mem_t["categorization_method"] = "USER_CORRECTED"
                    mem_t["confidence_score"] = Decimal("1.00")
                    mem_t["is_reviewed"] = True

            return tx_dict
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def get_monthly_summary_db(
        self,
        user_id: str,
        year_month: str = "2026-10",
        db: Optional[AsyncSession] = None,
    ) -> MonthlySpendingSummaryResult:
        """Calculate monthly spending rollup from PostgreSQL transactions."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            start_date, next_month_date = _parse_year_month_bounds(year_month)
            stmt = select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date < next_month_date,
            )
            res = await session.execute(stmt)
            month_txs = res.scalars().all()

            total_debit = Decimal("0.00")
            total_credit = Decimal("0.00")
            category_breakdown: Dict[str, Decimal] = {}

            for t in month_txs:
                amt = t.amount
                if t.transaction_type == "DEBIT":
                    total_debit += amt
                    cat = t.category_id
                    category_breakdown[cat] = category_breakdown.get(cat, Decimal("0.00")) + amt
                else:
                    total_credit += amt

            net_savings = total_credit - total_debit
            savings_rate = (
                round((net_savings / total_credit * Decimal("100.0")), 2) if total_credit > 0 else Decimal("0.00")
            )

            return MonthlySpendingSummaryResult(
                user_id=user_id,
                year_month=year_month,
                total_debit=float(total_debit),
                total_credit=float(total_credit),
                net_savings=float(net_savings),
                savings_rate_pct=float(savings_rate),
                transaction_count=len(month_txs),
                category_breakdown={
                    k: float(v) for k, v in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
                },
            )
        finally:
            if owns_session:
                await session.close()

    async def add_manual_transaction_db(
        self,
        user_id: str,
        transaction_date: str,
        amount: Decimal,
        description: str,
        transaction_type: str = "DEBIT",
        category_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Insert manual transaction directly into PostgreSQL."""
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        masked_desc = mask_sensitive_narrative(description)
        cat = category_id
        method = "MANUAL_USER"
        conf = Decimal("1.00")
        if not cat:
            cat, conf, method = categorize_transaction(masked_desc, transaction_type)

        tx_hash = hashlib.sha256(f"{transaction_date}:{amount}:{masked_desc}".encode("utf-8")).hexdigest()
        tx_uuid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        parsed_d = date.fromisoformat(transaction_date)

        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            await ensure_category_exists(session, cat)

            tx_entity = Transaction(
                id=tx_uuid,
                upload_id=None,
                user_id=user_id,
                transaction_date=parsed_d,
                amount=amount,
                transaction_type=transaction_type,
                masked_description=masked_desc,
                category_id=cat,
                categorization_method=method,
                confidence_score=conf,
                is_reviewed=True,
                dedupe_hash=tx_hash,
                created_at=now,
            )
            session.add(tx_entity)

            if owns_session:
                await session.commit()
            else:
                await session.flush()

            tx_record = {
                "id": str(tx_uuid),
                "upload_id": "manual-entry",
                "user_id": user_id,
                "transaction_date": transaction_date,
                "amount": amount,
                "transaction_type": transaction_type,
                "masked_description": masked_desc,
                "category_id": cat,
                "categorization_method": method,
                "confidence_score": conf,
                "is_reviewed": True,
                "dedupe_hash": tx_hash,
                "created_at": now.isoformat(),
            }
            _TRANSACTIONS_STORE.setdefault(user_id, []).append(tx_record)
            return tx_record
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()
