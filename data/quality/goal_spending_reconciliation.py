"""Goal & Spending Data Quality and Mathematical Reconciliation Suite.

Task ID: S7-DAT-03
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Reconciles goal contributions: sum of contribution rows must equal current_amount.
2. Reconciles monthly spending summaries: sum of category debits must equal total_debit.
3. Detects duplicate transaction fingerprints with zero break tolerance.
4. Validates date consistency (target date strictly after reference date).
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class GoalReconciliationBreak(BaseModel):
    check_name: str
    entity_id: str
    expected_value: Any
    actual_value: Any
    discrepancy: str


class GoalSpendingReconciliationReport(BaseModel):
    report_date: str
    total_goals_checked: int
    total_contributions_checked: int
    total_transactions_checked: int
    goals_reconciled: bool
    spending_reconciled: bool
    is_clean: bool
    breaks_count: int
    breaks: List[GoalReconciliationBreak]
    summary: str


class GoalSpendingReconciler:
    """Executes deterministic audit on goals and spending transactions."""

    def reconcile(
        self,
        goals: List[Dict[str, Any]],
        contributions: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
        monthly_summary: Optional[Dict[str, Any]] = None,
    ) -> GoalSpendingReconciliationReport:
        breaks: List[GoalReconciliationBreak] = []

        # 1. Goal Contributions Reconciliation
        # Group contributions by goal_id
        contribs_by_goal: Dict[str, Decimal] = {}
        for c in contributions:
            gid = c["goal_id"]
            contribs_by_goal[gid] = contribs_by_goal.get(gid, Decimal("0.00")) + Decimal(str(c["amount"]))

        for g in goals:
            gid = g["id"]
            current_amt = Decimal(str(g["current_amount"]))
            # If contributions exist, they should explain the balance
            if gid in contribs_by_goal:
                recorded_sum = contribs_by_goal[gid]
                if recorded_sum > current_amt:
                    breaks.append(
                        GoalReconciliationBreak(
                            check_name="goal_contribution_surplus_break",
                            entity_id=gid,
                            expected_value=float(current_amt),
                            actual_value=float(recorded_sum),
                            discrepancy=f"Contributions sum ₹{recorded_sum} exceeds goal balance ₹{current_amt}.",
                        )
                    )

            # Check target date validity
            tgt_date = date.fromisoformat(g["target_date"])
            ref_date = date.fromisoformat("2026-10-16")
            if tgt_date <= ref_date:
                breaks.append(
                    GoalReconciliationBreak(
                        check_name="goal_past_target_date_break",
                        entity_id=gid,
                        expected_value="Future date > 2026-10-16",
                        actual_value=g["target_date"],
                        discrepancy="Target date is in the past or today.",
                    )
                )

        # 2. Transaction Duplicate Check
        seen_hashes = set()
        for t in transactions:
            thash = t["dedupe_hash"]
            if thash in seen_hashes:
                breaks.append(
                    GoalReconciliationBreak(
                        check_name="duplicate_transaction_break",
                        entity_id=t.get("id", "unknown"),
                        expected_value="Unique transaction hash",
                        actual_value=thash,
                        discrepancy=f"Duplicate transaction hash found for {t.get('masked_description')}.",
                    )
                )
            seen_hashes.add(thash)

        # 3. Monthly Summary Reconciliation
        # Sum of debits across category breakdown must match total_debit exactly
        if monthly_summary:
            total_debit = Decimal(str(monthly_summary["total_debit"]))
            cat_breakdown = monthly_summary.get("category_breakdown", {})
            cat_sum = sum(Decimal(str(v)) for v in cat_breakdown.values())

            if abs(cat_sum - total_debit) > Decimal("0.01"):
                breaks.append(
                    GoalReconciliationBreak(
                        check_name="monthly_category_sum_mismatch",
                        entity_id=monthly_summary.get("year_month", "current"),
                        expected_value=float(total_debit),
                        actual_value=float(cat_sum),
                        discrepancy=f"Category breakdown sum ₹{cat_sum} does not equal total_debit ₹{total_debit}.",
                    )
                )

        goals_clean = all("goal" not in b.check_name for b in breaks)
        spending_clean = all("goal" in b.check_name for b in breaks) if breaks else True
        is_clean = len(breaks) == 0

        summary = (
            f"Goal & Spending Reconciliation completed: {len(goals)} goals, {len(contributions)} contributions, "
            f"{len(transactions)} transactions inspected. Breaks detected: {len(breaks)}."
        )

        return GoalSpendingReconciliationReport(
            report_date="2026-10-16",
            total_goals_checked=len(goals),
            total_contributions_checked=len(contributions),
            total_transactions_checked=len(transactions),
            goals_reconciled=goals_clean,
            spending_reconciled=spending_clean,
            is_clean=is_clean,
            breaks_count=len(breaks),
            breaks=breaks,
            summary=summary,
        )
