"""Unit & Scenario Tests for Market & Portfolio Data Quality Suite.

Task ID: S3-DAT-03
Tests warning vs blocking failures, stale quotes, holiday awareness,
duplicate observations, orphan items, invalid quantities, and partial valuation handling.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from data.quality.market_data_quality import (
    DQSeverity,
    MarketDataQualityChecker,
)


@pytest.fixture
def clean_market_dataset():
    ref_time = datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)  # Friday
    quotes = [
        {
            "id": "q1",
            "symbol": "RELIANCE",
            "price": Decimal("2500.00"),
            "observed_at": (ref_time - timedelta(hours=2)).isoformat(),
        },
        {
            "id": "q2",
            "symbol": "TCS",
            "price": Decimal("3500.00"),
            "observed_at": (ref_time - timedelta(hours=3)).isoformat(),
        },
    ]
    watchlists = [{"id": "wl1", "user_id": "usr-shivraj-001", "name": "Tech & Energy"}]
    watchlist_items = [
        {"id": "wli1", "watchlist_id": "wl1", "symbol": "RELIANCE"},
        {"id": "wli2", "watchlist_id": "wl1", "symbol": "TCS"},
    ]
    portfolios = [{"id": "p1", "user_id": "usr-shivraj-001", "name": "Growth"}]
    holdings = [
        {
            "id": "h1",
            "portfolio_id": "p1",
            "symbol": "RELIANCE",
            "quantity": Decimal("10"),
            "cost_basis_per_share": Decimal("2400.00"),
        },
        {
            "id": "h2",
            "portfolio_id": "p1",
            "symbol": "TCS",
            "quantity": Decimal("5"),
            "cost_basis_per_share": Decimal("3400.00"),
        },
    ]
    return quotes, watchlists, watchlist_items, portfolios, holdings, ref_time


def test_clean_market_dataset_passes(clean_market_dataset):
    quotes, watchlists, watchlist_items, portfolios, holdings, ref_time = clean_market_dataset
    checker = MarketDataQualityChecker()
    report = checker.evaluate(
        quotes=quotes,
        watchlists=watchlists,
        watchlist_items=watchlist_items,
        portfolios=portfolios,
        holdings=holdings,
        reference_time=ref_time,
    )
    assert report.is_clean is True
    assert report.blocking_violations_count == 0
    assert report.warning_violations_count == 0
    assert len(report.violations) == 0


def test_detects_stale_weekday_vs_weekend_quote(clean_market_dataset):
    quotes, watchlists, watchlist_items, portfolios, holdings, ref_time = clean_market_dataset

    # 1. Stale quote on a weekday (30 hours old) -> BLOCKING
    quotes[0]["observed_at"] = (ref_time - timedelta(hours=30)).isoformat()

    checker = MarketDataQualityChecker()
    report = checker.evaluate(
        quotes=quotes,
        watchlists=watchlists,
        watchlist_items=watchlist_items,
        portfolios=portfolios,
        holdings=holdings,
        reference_time=ref_time,
    )
    assert report.is_clean is False
    assert report.blocking_violations_count == 1
    v = report.violations[0]
    assert v.rule_name == "QUOTE_FRESHNESS"
    assert v.severity == DQSeverity.BLOCKING
    assert v.affected_symbol == "RELIANCE"

    # 2. Stale quote observed over weekend (Sunday reference time, 30 hours old) -> WARNING
    sunday_ref = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)
    quotes[0]["observed_at"] = (sunday_ref - timedelta(hours=30)).isoformat()
    quotes[1]["observed_at"] = (sunday_ref - timedelta(hours=2)).isoformat()
    report_weekend = checker.evaluate(
        quotes=quotes,
        watchlists=watchlists,
        watchlist_items=watchlist_items,
        portfolios=portfolios,
        holdings=holdings,
        reference_time=sunday_ref,
    )
    assert report_weekend.is_clean is True  # No blocking failure!
    assert report_weekend.has_warnings is True
    assert report_weekend.warning_violations_count == 1
    v_sun = report_weekend.violations[0]
    assert v_sun.severity == DQSeverity.WARNING


def test_detects_duplicate_quote_and_orphan_watchlist_item(clean_market_dataset):
    quotes, watchlists, watchlist_items, portfolios, holdings, ref_time = clean_market_dataset

    # Inject duplicate quote
    quotes.append(quotes[0].copy())

    # Inject orphan watchlist item (non-existent watchlist id)
    watchlist_items.append({"id": "wli99", "watchlist_id": "non-existent-wl", "symbol": "INFY"})

    checker = MarketDataQualityChecker()
    report = checker.evaluate(
        quotes=quotes,
        watchlists=watchlists,
        watchlist_items=watchlist_items,
        portfolios=portfolios,
        holdings=holdings,
        reference_time=ref_time,
    )
    assert report.is_clean is False
    rule_names = [v.rule_name for v in report.violations]
    assert "DUPLICATE_QUOTE_OBSERVATION" in rule_names
    assert "ORPHAN_WATCHLIST_ITEM" in rule_names


def test_detects_invalid_holding_quantity_and_negative_cost(clean_market_dataset):
    quotes, watchlists, watchlist_items, portfolios, holdings, ref_time = clean_market_dataset

    # Zero or negative quantity
    holdings.append(
        {
            "id": "h_bad1",
            "portfolio_id": "p1",
            "symbol": "RELIANCE",
            "quantity": Decimal("-5"),
            "cost_basis_per_share": Decimal("100"),
        }
    )
    # Negative cost basis
    holdings.append(
        {
            "id": "h_bad2",
            "portfolio_id": "p1",
            "symbol": "TCS",
            "quantity": Decimal("2"),
            "cost_basis_per_share": Decimal("-50"),
        }
    )

    checker = MarketDataQualityChecker()
    report = checker.evaluate(
        quotes=quotes,
        watchlists=watchlists,
        watchlist_items=watchlist_items,
        portfolios=portfolios,
        holdings=holdings,
        reference_time=ref_time,
    )
    rule_names = [v.rule_name for v in report.violations]
    assert "INVALID_HOLDING_QUANTITY" in rule_names
    assert "NEGATIVE_COST_BASIS" in rule_names


def test_partial_valuation_generates_warning_not_blocking(clean_market_dataset):
    quotes, watchlists, watchlist_items, portfolios, holdings, ref_time = clean_market_dataset

    # Holding for which quote is not available
    holdings.append(
        {
            "id": "h_unquoted",
            "portfolio_id": "p1",
            "symbol": "UNQUOTED_CORP",
            "quantity": Decimal("10"),
            "cost_basis_per_share": Decimal("500"),
        }
    )

    checker = MarketDataQualityChecker()
    report = checker.evaluate(
        quotes=quotes,
        watchlists=watchlists,
        watchlist_items=watchlist_items,
        portfolios=portfolios,
        holdings=holdings,
        reference_time=ref_time,
    )

    # Partial valuation should trigger WARNING, not BLOCKING
    assert report.is_clean is True
    assert report.has_warnings is True
    v = [v for v in report.violations if v.rule_name == "PARTIAL_PORTFOLIO_VALUATION"]
    assert len(v) == 1
    assert v[0].severity == DQSeverity.WARNING
    assert "UNQUOTED_CORP" in v[0].details
