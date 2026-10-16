"""
FinEx Core Data Quality Check Suite (Task: S1-DAT-03)
Author: Shivraj Dhote
Date: 16 October 2026

Implements verifiable data quality rules for core operational records:
1. Non-null IDs (users, portfolios, holdings)
2. Valid UTC timestamps (created_at <= updated_at)
3. Unique user emails
4. Positive holding quantities (quantity > 0)
5. Strict portfolio and holding ownership (no orphans)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class RuleViolation:
    rule_name: str
    table_name: str
    record_id: Optional[str]
    details: str


@dataclass
class DQReport:
    total_records_checked: int
    passed_rules: int
    failed_rules: int
    violations: List[RuleViolation] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0


class CoreDataQualityChecker:
    def __init__(self):
        pass

    def evaluate(
        self,
        users: List[Dict[str, Any]],
        portfolios: List[Dict[str, Any]],
        holdings: List[Dict[str, Any]],
    ) -> DQReport:
        violations: List[RuleViolation] = []
        total_records = len(users) + len(portfolios) + len(holdings)

        # Rule 1 & 2 & 3: Check Users
        seen_emails = set()
        user_ids = set()

        for u in users:
            uid = u.get("id")
            email = u.get("email")

            # Check Non-Null ID
            if not uid:
                violations.append(
                    RuleViolation(
                        rule_name="RULE_NON_NULL_IDS",
                        table_name="users",
                        record_id=None,
                        details="User record has null or empty ID",
                    )
                )
            else:
                user_ids.add(uid)

            # Check Unique Email
            if email:
                if email.lower() in seen_emails:
                    violations.append(
                        RuleViolation(
                            rule_name="RULE_UNIQUE_EMAILS",
                            table_name="users",
                            record_id=str(uid),
                            details=f"Duplicate email detected: '{email}'",
                        )
                    )
                seen_emails.add(email.lower())
            else:
                violations.append(
                    RuleViolation(
                        rule_name="RULE_NON_NULL_EMAIL",
                        table_name="users",
                        record_id=str(uid),
                        details="User record has null email",
                    )
                )

            # Check Timestamps
            created_at = u.get("created_at")
            updated_at = u.get("updated_at")
            if created_at and updated_at and created_at > updated_at:
                violations.append(
                    RuleViolation(
                        rule_name="RULE_VALID_TIMESTAMPS",
                        table_name="users",
                        record_id=str(uid),
                        details=f"created_at ({created_at}) is later than updated_at ({updated_at})",
                    )
                )

        # Rule 1, 2 & 5: Check Portfolios
        portfolio_ids = set()
        for p in portfolios:
            pid = p.get("id")
            p_uid = p.get("user_id")

            if not pid:
                violations.append(
                    RuleViolation(
                        rule_name="RULE_NON_NULL_IDS",
                        table_name="portfolios",
                        record_id=None,
                        details="Portfolio record has null or empty ID",
                    )
                )
            else:
                portfolio_ids.add(pid)

            if p_uid not in user_ids:
                violations.append(
                    RuleViolation(
                        rule_name="RULE_PORTFOLIO_OWNERSHIP",
                        table_name="portfolios",
                        record_id=str(pid),
                        details=f"Orphan portfolio: user_id '{p_uid}' does not exist",
                    )
                )

        # Rule 1, 4 & 5: Check Holdings
        for h in holdings:
            hid = h.get("id")
            h_pid = h.get("portfolio_id")
            qty = h.get("quantity")

            if not hid:
                violations.append(
                    RuleViolation(
                        rule_name="RULE_NON_NULL_IDS",
                        table_name="portfolio_holdings",
                        record_id=None,
                        details="Holding record has null or empty ID",
                    )
                )

            if h_pid not in portfolio_ids:
                violations.append(
                    RuleViolation(
                        rule_name="RULE_PORTFOLIO_OWNERSHIP",
                        table_name="portfolio_holdings",
                        record_id=str(hid),
                        details=f"Orphan holding: portfolio_id '{h_pid}' does not exist",
                    )
                )

            if qty is None or Decimal(str(qty)) <= Decimal("0"):
                violations.append(
                    RuleViolation(
                        rule_name="RULE_POSITIVE_QUANTITY",
                        table_name="portfolio_holdings",
                        record_id=str(hid),
                        details=f"Invalid non-positive holding quantity: {qty}",
                    )
                )

        return DQReport(
            total_records_checked=total_records,
            passed_rules=5 - len(set(v.rule_name for v in violations)),
            failed_rules=len(set(v.rule_name for v in violations)),
            violations=violations,
        )
