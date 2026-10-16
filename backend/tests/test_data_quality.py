from datetime import datetime, timezone
from decimal import Decimal

import pytest
from data.quality.core_data_quality import CoreDataQualityChecker


@pytest.fixture
def clean_dataset():
    now = datetime.now(timezone.utc)
    users = [
        {
            "id": "u1",
            "email": "user1@example.com",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "u2",
            "email": "user2@example.com",
            "created_at": now,
            "updated_at": now,
        },
    ]
    portfolios = [
        {"id": "p1", "user_id": "u1", "name": "Primary Portfolio"},
        {"id": "p2", "user_id": "u2", "name": "Retirement Portfolio"},
    ]
    holdings = [
        {"id": "h1", "portfolio_id": "p1", "symbol": "NSE:RELIANCE", "quantity": Decimal("10")},
        {"id": "h2", "portfolio_id": "p2", "symbol": "NSE:TCS", "quantity": Decimal("5.5")},
    ]
    return users, portfolios, holdings


def test_clean_data_passes_all_checks(clean_dataset):
    users, portfolios, holdings = clean_dataset
    checker = CoreDataQualityChecker()
    report = checker.evaluate(users, portfolios, holdings)
    assert report.is_clean is True
    assert len(report.violations) == 0


def test_detects_injected_bad_rows(clean_dataset):
    users, portfolios, holdings = clean_dataset

    # Inject 1: Duplicate email
    users.append({"id": "u3", "email": "user1@example.com"})

    # Inject 2: Null ID in portfolio
    portfolios.append({"id": None, "user_id": "u1", "name": "Broken"})

    # Inject 3: Orphan holding (referencing non-existent portfolio)
    holdings.append({"id": "h3", "portfolio_id": "p_non_existent", "quantity": Decimal("1")})

    # Inject 4: Negative holding quantity
    holdings.append({"id": "h4", "portfolio_id": "p1", "quantity": Decimal("-10")})

    checker = CoreDataQualityChecker()
    report = checker.evaluate(users, portfolios, holdings)

    assert report.is_clean is False
    assert len(report.violations) >= 4

    violation_rules = [v.rule_name for v in report.violations]
    assert "RULE_UNIQUE_EMAILS" in violation_rules
    assert "RULE_NON_NULL_IDS" in violation_rules
    assert "RULE_PORTFOLIO_OWNERSHIP" in violation_rules
    assert "RULE_POSITIVE_QUANTITY" in violation_rules
