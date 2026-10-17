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
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

# In-memory operational store for isolated testing/development baseline
_UPLOADS_STORE: Dict[str, Dict[str, Any]] = {}  # upload_id -> upload_dict
_TRANSACTIONS_STORE: Dict[str, List[Dict[str, Any]]] = {}  # user_id -> list of transactions
_PREVIEWS_STORE: Dict[str, Dict[str, Any]] = {}  # preview_id -> preview_dict


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
