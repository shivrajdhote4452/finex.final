"""Unit tests for SQLAlchemy core models and operational storage adapter.

Task ID: S1-DAT-02
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from backend.app.database import SQLAlchemyOperationalStorage
from backend.app.models.core import (
    ApplicationEvent,
    Portfolio,
    PortfolioHolding,
    User,
    UserConsent,
    UserProfile,
)


def test_user_model_initialization():
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="shivraj@example.com",
        provider="google",
        provider_subject="sub_12345",
        is_active=True,
        is_verified=True,
    )

    assert user.id == user_id
    assert user.email == "shivraj@example.com"
    assert user.provider == "google"
    assert user.provider_subject == "sub_12345"
    assert user.is_active is True
    assert user.is_verified is True


def test_user_profile_relationship():
    user = User(
        email="investor@example.com",
        provider="google",
        provider_subject="sub_999",
    )
    profile = UserProfile(
        user=user,
        full_name="Shivraj Dhote",
        display_name="Shivraj",
        country="IND",
        experience_level="MODERATE",
        onboarding_completed=True,
    )

    assert profile.user == user
    assert profile.display_name == "Shivraj"
    assert profile.experience_level == "MODERATE"


def test_user_consent_model():
    user = User(email="consent@example.com", provider="google", provider_subject="sub_001")
    consent = UserConsent(
        user=user,
        consent_version="v1.0",
        terms_accepted=True,
        privacy_accepted=True,
        educational_disclaimer_accepted=True,
        ip_address="127.0.0.1",
    )

    assert consent.consent_version == "v1.0"
    assert consent.educational_disclaimer_accepted is True


def test_portfolio_and_holdings_model():
    user = User(email="portfolio@example.com", provider="google", provider_subject="sub_002")
    portfolio = Portfolio(
        user=user,
        name="Equity Wealth Fund",
        currency="INR",
        is_default=True,
    )

    holding = PortfolioHolding(
        portfolio=portfolio,
        symbol="RELIANCE",
        asset_class="EQUITY",
        quantity=Decimal("10.000000"),
        cost_basis_per_share=Decimal("2450.5000"),
        currency="INR",
        purchase_date=date(2026, 10, 15),
    )

    assert holding.symbol == "RELIANCE"
    assert holding.quantity == Decimal("10.000000")
    assert holding.cost_basis_per_share == Decimal("2450.5000")
    assert portfolio.holdings == [holding]


def test_application_event_model():
    event = ApplicationEvent(
        event_type="ORDER_EXECUTED",
        correlation_id="corr-987123",
        payload={"symbol": "TCS", "shares": 5, "price": 3600},
        ip_address="192.168.1.1",
    )

    assert event.event_type == "ORDER_EXECUTED"
    assert event.correlation_id == "corr-987123"
    assert event.payload["symbol"] == "TCS"


@pytest.mark.asyncio
async def test_operational_storage_safe_connection_info():
    storage = SQLAlchemyOperationalStorage()
    info = await storage.get_connection_info()

    assert "status" in info
    assert info["dialect"] == "postgresql"
    assert "password" not in str(info)
    assert "postgres:postgres" not in str(info)
    assert info["pool_size"] == 10
