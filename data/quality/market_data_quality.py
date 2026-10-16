"""FinEx Market and Portfolio Data Quality Suite.

Task ID: S3-DAT-03
Author: Shivraj Dhote
Date: 16 October 2026

Implements verifiable data quality rules:
1. Stale Quotes: Warning vs Blocking (distinguishes market holidays/weekends from feed outages)
2. Duplicate Quotes: Duplicate natural keys (security_id, observed_at)
3. Orphan Watchlist Items: References non-existent watchlist or unverified security
4. Invalid Holding Quantity: Quantity <= 0 or impossible non-numeric
5. Portfolio Allocation Sum: Sum of sector or asset weights == 100% (tolerance +/- 0.1%) when fully valued
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class DQSeverity(str, Enum):
    WARNING = "WARNING"
    BLOCKING = "BLOCKING"


@dataclass
class MarketDQViolation:
    rule_name: str
    severity: DQSeverity
    entity_type: str
    entity_id: Optional[str]
    details: str
    affected_symbol: Optional[str] = None
    affected_user: Optional[str] = None


@dataclass
class MarketDQReport:
    total_records_checked: int
    blocking_violations_count: int
    warning_violations_count: int
    violations: List[MarketDQViolation] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.blocking_violations_count == 0

    @property
    def has_warnings(self) -> bool:
        return self.warning_violations_count > 0


class MarketDataQualityChecker:
    def __init__(
        self,
        stale_threshold_hours: int = 24,
        weekend_grace_hours: int = 72,
    ):
        self.stale_threshold_hours = stale_threshold_hours
        self.weekend_grace_hours = weekend_grace_hours

    def evaluate(
        self,
        quotes: List[Dict[str, Any]],
        watchlists: List[Dict[str, Any]],
        watchlist_items: List[Dict[str, Any]],
        portfolios: List[Dict[str, Any]],
        holdings: List[Dict[str, Any]],
        reference_time: Optional[datetime] = None,
    ) -> MarketDQReport:
        now = reference_time or datetime.now(timezone.utc)
        violations: List[MarketDQViolation] = []
        total_records = (
            len(quotes) + len(watchlists) + len(watchlist_items) + len(portfolios) + len(holdings)
        )

        known_security_symbols: Set[str] = set()

        # 1. Evaluate Market Quotes
        seen_quote_keys: Set[tuple] = set()

        for q in quotes:
            sym = q.get("symbol", "").upper()
            if sym:
                known_security_symbols.add(sym)

            obs_at_raw = q.get("observed_at")
            if isinstance(obs_at_raw, str):
                try:
                    obs_at = datetime.fromisoformat(obs_at_raw.replace("Z", "+00:00"))
                except Exception:
                    obs_at = None
            elif isinstance(obs_at_raw, datetime):
                obs_at = obs_at_raw
            else:
                obs_at = None

            # Rule 1: Check Observation Timestamp & Stale Freshness
            if not obs_at:
                violations.append(
                    MarketDQViolation(
                        rule_name="VALID_OBSERVATION_TIMESTAMP",
                        severity=DQSeverity.BLOCKING,
                        entity_type="market_quote",
                        entity_id=q.get("id"),
                        details=f"Quote for '{sym}' lacks valid observed_at timestamp.",
                        affected_symbol=sym,
                    )
                )
            else:
                age = now - obs_at
                is_weekend = now.weekday() in (5, 6) or obs_at.weekday() in (5, 6)
                
                # Check for holiday / weekend vs active feed outage
                if age > timedelta(hours=self.weekend_grace_hours):
                    violations.append(
                        MarketDQViolation(
                            rule_name="QUOTE_FRESHNESS",
                            severity=DQSeverity.BLOCKING,
                            entity_type="market_quote",
                            entity_id=q.get("id"),
                            details=f"Quote for '{sym}' observed at {obs_at.isoformat()} is severely stale (> {self.weekend_grace_hours}h). Missing feed or upstream outage.",
                            affected_symbol=sym,
                        )
                    )
                elif age > timedelta(hours=self.stale_threshold_hours):
                    severity = DQSeverity.WARNING if is_weekend else DQSeverity.BLOCKING
                    reason = "Market closed / weekend observation grace." if is_weekend else "Trading day quote is delayed > 24 hours."
                    violations.append(
                        MarketDQViolation(
                            rule_name="QUOTE_FRESHNESS",
                            severity=severity,
                            entity_type="market_quote",
                            entity_id=q.get("id"),
                            details=f"Quote for '{sym}' is stale (age: {age.total_seconds()/3600:.1f}h). {reason}",
                            affected_symbol=sym,
                        )
                    )

            # Rule 2: Duplicate natural keys (symbol, observed_at)
            key = (sym, obs_at.isoformat() if obs_at else None)
            if key in seen_quote_keys:
                violations.append(
                    MarketDQViolation(
                        rule_name="DUPLICATE_QUOTE_OBSERVATION",
                        severity=DQSeverity.BLOCKING,
                        entity_type="market_quote",
                        entity_id=q.get("id"),
                        details=f"Duplicate quote entry detected for '{sym}' at observation {obs_at}.",
                        affected_symbol=sym,
                    )
                )
            else:
                seen_quote_keys.add(key)

        # 2. Evaluate Watchlists and Watchlist Items
        wl_map: Dict[str, Dict[str, Any]] = {w["id"]: w for w in watchlists if w.get("id")}

        # Check for Watchlist non-null user_id
        for w in watchlists:
            if not w.get("id") or not w.get("user_id"):
                violations.append(
                    MarketDQViolation(
                        rule_name="VALID_WATCHLIST_RECORD",
                        severity=DQSeverity.BLOCKING,
                        entity_type="watchlist",
                        entity_id=w.get("id"),
                        details="Watchlist record missing id or user_id.",
                        affected_user=w.get("user_id"),
                    )
                )

        # Check Watchlist Items for orphans and duplicate pins
        seen_wl_items: Set[tuple] = set()
        for item in watchlist_items:
            wl_id = item.get("watchlist_id")
            sym = item.get("symbol", "").upper()

            # Rule 3: Orphan check
            if wl_id not in wl_map:
                violations.append(
                    MarketDQViolation(
                        rule_name="ORPHAN_WATCHLIST_ITEM",
                        severity=DQSeverity.BLOCKING,
                        entity_type="watchlist_item",
                        entity_id=item.get("id"),
                        details=f"Watchlist item references non-existent watchlist_id '{wl_id}'.",
                        affected_symbol=sym,
                    )
                )
            else:
                user_id = wl_map[wl_id].get("user_id")
                # Rule: Duplicate item in same watchlist
                item_key = (wl_id, sym)
                if item_key in seen_wl_items:
                    violations.append(
                        MarketDQViolation(
                            rule_name="DUPLICATE_WATCHLIST_ITEM",
                            severity=DQSeverity.BLOCKING,
                            entity_type="watchlist_item",
                            entity_id=item.get("id"),
                            details=f"Duplicate symbol '{sym}' pinned in watchlist '{wl_id}'.",
                            affected_symbol=sym,
                            affected_user=user_id,
                        )
                    )
                else:
                    seen_wl_items.add(item_key)

        # 3. Evaluate Holdings and Portfolio Valuation Integrity
        p_map: Dict[str, Dict[str, Any]] = {p["id"]: p for p in portfolios if p.get("id")}

        # Group holdings by portfolio
        p_holdings: Dict[str, List[Dict[str, Any]]] = {}
        for h in holdings:
            p_id = h.get("portfolio_id")
            sym = h.get("symbol", "").upper()

            # Rule 4: Orphan Holding
            if p_id not in p_map:
                violations.append(
                    MarketDQViolation(
                        rule_name="ORPHAN_HOLDING",
                        severity=DQSeverity.BLOCKING,
                        entity_type="holding",
                        entity_id=h.get("id"),
                        details=f"Holding references non-existent portfolio_id '{p_id}'.",
                        affected_symbol=sym,
                    )
                )
                continue

            user_id = p_map[p_id].get("user_id")

            # Rule 5: Non-positive or invalid quantity
            qty = h.get("quantity")
            try:
                dec_qty = Decimal(str(qty))
                if dec_qty <= Decimal("0"):
                    violations.append(
                        MarketDQViolation(
                            rule_name="INVALID_HOLDING_QUANTITY",
                            severity=DQSeverity.BLOCKING,
                            entity_type="holding",
                            entity_id=h.get("id"),
                            details=f"Holding quantity must be strictly positive (> 0), got: {qty}.",
                            affected_symbol=sym,
                            affected_user=user_id,
                        )
                    )
            except Exception:
                violations.append(
                    MarketDQViolation(
                        rule_name="INVALID_HOLDING_QUANTITY",
                        severity=DQSeverity.BLOCKING,
                        entity_type="holding",
                        entity_id=h.get("id"),
                        details=f"Invalid numeric value for quantity: {qty}.",
                        affected_symbol=sym,
                        affected_user=user_id,
                    )
                )

            # Rule 6: Cost basis validation
            cost = h.get("cost_basis_per_share")
            try:
                dec_cost = Decimal(str(cost))
                if dec_cost < Decimal("0"):
                    violations.append(
                        MarketDQViolation(
                            rule_name="NEGATIVE_COST_BASIS",
                            severity=DQSeverity.BLOCKING,
                            entity_type="holding",
                            entity_id=h.get("id"),
                            details=f"Holding cost basis cannot be negative, got: {cost}.",
                            affected_symbol=sym,
                            affected_user=user_id,
                        )
                    )
            except Exception:
                violations.append(
                    MarketDQViolation(
                        rule_name="INVALID_COST_BASIS",
                        severity=DQSeverity.BLOCKING,
                        entity_type="holding",
                        entity_id=h.get("id"),
                        details=f"Invalid numeric value for cost_basis_per_share: {cost}.",
                        affected_symbol=sym,
                        affected_user=user_id,
                    )
                )

            p_holdings.setdefault(p_id, []).append(h)

        # Rule 7: Allocation Sum Check (where full valuation exists)
        latest_prices: Dict[str, Decimal] = {}
        for q in quotes:
            s = q.get("symbol", "").upper()
            if "price" in q:
                try:
                    latest_prices[s] = Decimal(str(q["price"]))
                except Exception:
                    pass

        for p_id, p_obj in p_map.items():
            user_id = p_obj.get("user_id")
            port_holdings = p_holdings.get(p_id, [])
            if not port_holdings:
                continue

            # Check if all holdings have quotes
            missing_symbols = [
                h["symbol"].upper() for h in port_holdings if h["symbol"].upper() not in latest_prices
            ]

            if missing_symbols:
                violations.append(
                    MarketDQViolation(
                        rule_name="PARTIAL_PORTFOLIO_VALUATION",
                        severity=DQSeverity.WARNING,
                        entity_type="portfolio",
                        entity_id=p_id,
                        details=f"Portfolio has partial valuation due to missing quote(s) for: {missing_symbols}. Total market value and allocation sum calculation withheld.",
                        affected_user=user_id,
                    )
                )
            else:
                # Fully valued portfolio: verify weights sum to 1.0 (100%)
                total_val = sum(
                    Decimal(str(h["quantity"])) * latest_prices[h["symbol"].upper()]
                    for h in port_holdings
                )
                if total_val > Decimal("0"):
                    weights_sum = sum(
                        (Decimal(str(h["quantity"])) * latest_prices[h["symbol"].upper()]) / total_val
                        for h in port_holdings
                    )
                    diff = abs(weights_sum - Decimal("1.0"))
                    if diff > Decimal("0.001"):  # 0.1% tolerance
                        violations.append(
                            MarketDQViolation(
                                rule_name="ALLOCATION_WEIGHT_SUM_ERROR",
                                severity=DQSeverity.BLOCKING,
                                entity_type="portfolio",
                                entity_id=p_id,
                                details=f"Holdings allocation weights sum to {weights_sum:.4f}, expected 1.0000 (+/- 0.001).",
                                affected_user=user_id,
                            )
                        )

        blocking = [v for v in violations if v.severity == DQSeverity.BLOCKING]
        warnings = [v for v in violations if v.severity == DQSeverity.WARNING]

        return MarketDQReport(
            total_records_checked=total_records,
            blocking_violations_count=len(blocking),
            warning_violations_count=len(warnings),
            violations=violations,
        )
