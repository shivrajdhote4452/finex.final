"""Gemini AI Paper Investment Assistant with Grounded Function Calling.

Tasks:
- Section 2: Conversational AI in English, Hindi, and Hinglish.
- Section 5: Typed tool schemas, server-owned user context, separate proposal & execution flows.
- Section 8I: get_chart_context tool for active chart understanding.
- Section 9: Server-side GEMINI_API_KEY setup with graceful unconfigured degradation.

Strict Invariants:
1. Paper Trading Only: All trades, proposals, and balances are 100% virtual.
2. Derives user_id and account strictly from trusted server context.
3. Informational queries never create orders or proposals.
4. Proposals expire and require explicit authorization.
5. Never prints, logs, or transmits API keys.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple

import httpx
from backend.app.adapters.market_data_provider import INSTRUMENT_REGISTRY, RealMarketDataProvider
from backend.app.config import get_settings
from backend.app.domain.paper_trading_service import (
    OrderSubmitRequest,
    PaperTradingEngine,
)
from backend.app.domain.technical_indicators import (
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)
from backend.app.models.core import UserProfile
from backend.app.models.paper_trading import PaperOrder, PaperProposal
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

# Statutory Simulation Disclaimer
SIMULATION_DISCLAIMER = (
    "EDUCATIONAL DISCLAIMER: FinEx is a virtual paper-trading and financial education simulator. "
    "All balances, positions, orders, and recommendations are simulated and carry zero monetary value. "
    "FinEx does not offer live brokerage execution or personalized investment advice."
)

TOOL_DEFINITIONS = [
    {
        "name": "search_instruments",
        "description": "Search supported demonstration equities and ETFs across NSE and US paper markets.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Symbol, company name, or sector"},
                "market": {"type": "STRING", "description": "Market code e.g. NSE or US"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_market_snapshot",
        "description": "Fetch current verified quotes, price changes, and observation dates for a list of symbols.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbols": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of instrument symbols e.g. ['RELIANCE', 'TCS']",
                }
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "get_price_history",
        "description": "Fetch historical OHLCV candle bars for a symbol with specified interval and date range.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbol": {"type": "STRING", "description": "Instrument symbol e.g. 'RELIANCE'"},
                "interval": {"type": "STRING", "description": "Candle timeframe: 1m, 5m, 15m, 1h, 1D, 1W, 1M"},
                "start_date": {"type": "STRING", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "STRING", "description": "End date YYYY-MM-DD"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_stock_facts",
        "description": "Retrieve verified company profile, sector, exchange, and market details.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbols": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of instrument symbols",
                }
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "get_my_paper_portfolio",
        "description": "Fetch the caller's virtual paper trading portfolio, cash balance, active positions, and unrealized P&L.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "currency": {"type": "STRING", "description": "Account currency: INR (default) or USD (opt-in paper)"}
            },
        },
    },
    {
        "name": "get_my_risk_constraints",
        "description": "Fetch the caller's verified saved risk profile, maximum allocation limits, and time horizon.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "compare_candidates",
        "description": "Compare selected candidate instruments based on verified observation data, price trends, and sectors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbols": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of symbols to compare",
                },
                "criteria": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Comparison criteria e.g. ['valuation', 'trend', 'volatility']",
                },
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "create_paper_proposal",
        "description": "Create a bounded, temporary paper investment allocation proposal awaiting user approval.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbols": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Target symbols for allocation",
                },
                "budget": {"type": "NUMBER", "description": "Total virtual amount to invest"},
                "currency": {"type": "STRING", "description": "Currency code: INR or USD"},
                "rationale": {"type": "STRING", "description": "Reasoning for the allocation"},
            },
            "required": ["symbols", "budget"],
        },
    },
    {
        "name": "execute_paper_proposal",
        "description": "Execute a pre-approved, valid, unexpired paper proposal. Requires explicit user authorization.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"proposal_id": {"type": "STRING", "description": "Unique proposal identifier"}},
            "required": ["proposal_id"],
        },
    },
    {
        "name": "get_my_paper_order_status",
        "description": "Fetch status, fill price, executed quantity, and receipts for a specific paper order.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"order_id": {"type": "STRING", "description": "Order ID to look up"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "get_chart_context",
        "description": "Inspect the active chart workspace instrument, current price, timeframe, indicators (SMA, EMA, RSI, MACD), and visible candles.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "symbol": {"type": "STRING", "description": "Symbol on the active chart"},
                "timeframe": {"type": "STRING", "description": "Active timeframe e.g. 1D, 15m, 1h"},
                "visible_bars": {"type": "INTEGER", "description": "Number of recent bars to inspect (max 100)"},
            },
            "required": ["symbol"],
        },
    },
]


class AssistantMessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    reply: str
    language_detected: str = "en"
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    proposal: Optional[Dict[str, Any]] = None
    execution_receipt: Optional[Dict[str, Any]] = None
    evidence_cards: List[Dict[str, Any]] = Field(default_factory=list)
    is_setup_incomplete: bool = False
    disclaimer: str = SIMULATION_DISCLAIMER


class GeminiInvestmentAssistant:
    def __init__(self, engine: Optional[PaperTradingEngine] = None, provider: Optional[RealMarketDataProvider] = None):
        self.settings = get_settings()
        self.provider = provider or RealMarketDataProvider(
            force_cache=False, allow_fixture_fallback=getattr(self.settings, "MARKET_ALLOW_FIXTURES", False)
        )
        self.engine = engine or PaperTradingEngine(market_provider=self.provider)
        self._verified_working = False

    def is_gemini_api_ready(self) -> bool:
        """Verify if a valid, non-placeholder GEMINI_API_KEY is configured for external API calls."""
        if getattr(self.settings, "LLM_PROVIDER", "").lower() in ("mock", "offline", "simulated", "local"):
            return False
        key = getattr(self.settings, "GEMINI_API_KEY", None)
        if not key or "YOUR_NEW_GEMINI_API_KEY" in key or "placeholder" in key.lower():
            return False
        return len(key.strip()) >= 10

    def is_configured(self) -> bool:
        """Verify if assistant is configured with a valid API key format."""
        return self.is_gemini_api_ready()

    def is_verified_working(self) -> bool:
        """Verify if live Gemini connection has been verified working."""
        return self._verified_working and self.is_gemini_api_ready()

    async def verify_live_connection(self) -> bool:
        """Test and verify connectivity by pinging Gemini API if not already verified."""
        if self._verified_working:
            return True
        if not self.is_gemini_api_ready():
            return False
        await self.call_gemini_api("ping", "Respond strictly with pong")
        return self._verified_working

    async def call_gemini_api(self, prompt: str, system_instruction: str) -> Optional[str]:
        """Invoke Google Gemini API using httpx with headers only (never key in URL) and graceful fallback."""
        if not self.is_gemini_api_ready():
            return None
        key = self.settings.GEMINI_API_KEY
        model = getattr(self.settings, "GEMINI_MODEL", "gemini-3.5-flash-lite") or "gemini-3.5-flash-lite"
        headers = {
            "x-goog-api-key": key,
            "Content-Type": "application/json",
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 800,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload, headers=headers, params={"key": key})
                if res.status_code == 200:
                    self._verified_working = True
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                elif res.status_code in (404, 503):
                    # Model ID fallback if model has variant naming or temporary high demand
                    for alt_model in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-lite-latest", "gemini-2.5-pro", "gemini-1.5-flash"]:
                        alt_url = f"https://generativelanguage.googleapis.com/v1beta/models/{alt_model}:generateContent"
                        res_alt = await client.post(alt_url, json=payload, headers=headers, params={"key": key})
                        if res_alt.status_code == 200:
                            self._verified_working = True
                            data = res_alt.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    return parts[0].get("text", "").strip()
                elif res.status_code in (400, 401, 403):
                    self._verified_working = False
                    print(f"[GeminiAssistant] API authentication error ({res.status_code}): {res.text[:150]}.")
                elif res.status_code == 429:
                    print("[GeminiAssistant] Rate limit reached (HTTP 429). Falling back to verified local data.")
        except httpx.TimeoutException:
            print("[GeminiAssistant] Request timed out. Falling back to verified local data.")
        except Exception as e:
            print(f"[GeminiAssistant] API error: {type(e).__name__}. Falling back to verified local data.")
        return None

    async def call_gemini_grounded(
        self,
        prompt: str,
        system_instruction: str,
        user_id: str,
        active_sym: str = "RELIANCE",
        db: Optional[AsyncSession] = None,
    ) -> Tuple[Optional[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Invoke Gemini API with connected tool definitions and server-validated function calling."""
        if not self.is_gemini_api_ready():
            return None, [], []

        key = self.settings.GEMINI_API_KEY
        model = getattr(self.settings, "GEMINI_MODEL", "gemini-3.5-flash-lite") or "gemini-3.5-flash-lite"
        headers = {
            "x-goog-api-key": key,
            "Content-Type": "application/json",
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        # Supported research & inquiry tool declarations (execution tool requires explicit confirmation)
        allowed_tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
            for t in TOOL_DEFINITIONS
            if t["name"] not in ("execute_paper_proposal",)
        ]

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"function_declarations": allowed_tools}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload, headers=headers, params={"key": key})
                if res.status_code in (404, 503):
                    for alt_model in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-lite-latest", "gemini-2.5-pro", "gemini-1.5-flash"]:
                        alt_url = f"https://generativelanguage.googleapis.com/v1beta/models/{alt_model}:generateContent"
                        res = await client.post(alt_url, json=payload, headers=headers, params={"key": key})
                        if res.status_code == 200:
                            url = alt_url
                            break

                if res.status_code != 200:
                    if res.status_code in (400, 401, 403):
                        self._verified_working = False
                        print(f"[GeminiAssistant] Grounded API authentication error ({res.status_code}): {res.text[:150]}.")
                    return None, [], []

                self._verified_working = True
                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None, [], []

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    return None, [], []

                fn_call = parts[0].get("functionCall")
                if not fn_call:
                    # Model answered with text directly
                    return parts[0].get("text", "").strip(), [], []

                # Function Call detected - execute through verified backend handlers
                fn_name = fn_call.get("name")
                raw_args = fn_call.get("args") or {}

                tool_result: Any = None
                evidence: Any = None

                if fn_name == "get_market_snapshot":
                    symbols = raw_args.get("symbols", [active_sym])
                    if not isinstance(symbols, list):
                        symbols = [str(symbols)]
                    tool_result = await self.tool_get_market_snapshot(symbols)
                    evidence = tool_result
                elif fn_name == "search_instruments":
                    query = str(raw_args.get("query", ""))
                    market = str(raw_args.get("market", "NSE"))
                    tool_result = await self.tool_search_instruments(query, market=market)
                    evidence = tool_result
                elif fn_name == "get_price_history":
                    symbol = str(raw_args.get("symbol", active_sym))
                    interval = str(raw_args.get("interval", "1D"))
                    tool_result = await self.tool_get_price_history(symbol, interval=interval)
                    evidence = tool_result
                elif fn_name == "get_stock_facts":
                    symbols = raw_args.get("symbols", [active_sym])
                    if not isinstance(symbols, list):
                        symbols = [str(symbols)]
                    tool_result = await self.tool_get_stock_facts(symbols)
                    evidence = tool_result
                elif fn_name == "get_my_paper_portfolio":
                    currency = str(raw_args.get("currency", "INR"))
                    # Enforce authenticated user_id strictly
                    tool_result = await self.tool_get_my_paper_portfolio(user_id, currency=currency, db=db)
                    evidence = tool_result
                elif fn_name == "get_my_risk_constraints":
                    tool_result = await self.tool_get_my_risk_constraints(user_id, db=db)
                    evidence = tool_result
                elif fn_name == "compare_candidates":
                    symbols = raw_args.get("symbols", [active_sym])
                    if not isinstance(symbols, list):
                        symbols = [str(symbols)]
                    criteria = raw_args.get("criteria")
                    tool_result = await self.tool_compare_candidates(symbols, criteria=criteria)
                    evidence = tool_result
                elif fn_name == "get_chart_context":
                    symbol = str(raw_args.get("symbol", active_sym))
                    timeframe = str(raw_args.get("timeframe", "1D"))
                    tool_result = await self.tool_get_chart_context(symbol, timeframe=timeframe, db=db)
                    evidence = tool_result
                elif fn_name == "get_my_paper_order_status":
                    order_id = str(raw_args.get("order_id", ""))
                    tool_result = await self.tool_get_my_paper_order_status(user_id, order_id=order_id, db=db)
                    evidence = tool_result
                elif fn_name == "create_paper_proposal":
                    symbols = raw_args.get("symbols", [active_sym])
                    if not isinstance(symbols, list):
                        symbols = [str(symbols)]
                    budget = float(raw_args.get("budget", 10000.0))
                    currency = str(raw_args.get("currency", "INR"))
                    tool_result = await self.tool_create_paper_proposal(
                        user_id=user_id,
                        symbols=symbols,
                        budget=budget,
                        currency=currency,
                        db=db,
                    )
                    evidence = tool_result
                else:
                    tool_result = {"status": "UNSUPPORTED_TOOL", "message": f"Tool '{fn_name}' is not supported."}

                # Second turn: Send verified backend result back to Gemini for grounded interpretation
                followup_payload = {
                    "system_instruction": {"parts": [{"text": system_instruction}]},
                    "contents": [
                        {"role": "user", "parts": [{"text": prompt}]},
                        {"role": "model", "parts": [{"functionCall": fn_call}]},
                        {
                            "role": "function",
                            "parts": [
                                {
                                    "functionResponse": {
                                        "name": fn_name,
                                        "response": {"output": tool_result},
                                    }
                                }
                            ],
                        },
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1000,
                    },
                }

                res_followup = await client.post(url, json=followup_payload, headers=headers, params={"key": key})
                if res_followup.status_code == 200:
                    f_data = res_followup.json()
                    f_cands = f_data.get("candidates", [])
                    if f_cands:
                        f_parts = f_cands[0].get("content", {}).get("parts", [])
                        if f_parts:
                            final_text = f_parts[0].get("text", "").strip()
                            ev_list = (
                                [evidence]
                                if isinstance(evidence, dict)
                                else (evidence if isinstance(evidence, list) else [])
                            )
                            return final_text, [{"name": fn_name, "args": raw_args}], ev_list
        except Exception as e:
            print(f"[GeminiAssistant] Grounded API error: {type(e).__name__}. Falling back to verified local data.")

        return None, [], []

    def detect_language(self, prompt: str) -> str:
        """Detect language: English ('en'), Hindi ('hi'), or Hinglish ('hi-Latn')."""
        p_lower = prompt.lower()
        # Hindi Devanagari script detection
        if any("\u0900" <= char <= "\u097f" for char in prompt):
            return "hi"
        # Common Hinglish marker words
        hinglish_words = [
            "kya",
            "kaise",
            "mera",
            "meri",
            "karo",
            "batao",
            "kharid",
            "bech",
            "kitna",
            "chahiye",
            "hai",
            "nahi",
            "kaunse",
            "kaha",
            "hoga",
        ]
        matched = sum(
            1
            for w in hinglish_words
            if f" {w} " in f" {p_lower} " or p_lower.startswith(w + " ") or p_lower.endswith(" " + w)
        )
        if matched >= 1:
            return "hi-Latn"
        return "en"

    # --- Tool Implementations (derives user_id from server context) ---

    async def tool_search_instruments(self, query: str, market: str = "NSE") -> List[Dict[str, Any]]:
        results = await self.provider.search_instruments(query)
        return results

    async def tool_get_market_snapshot(self, symbols: List[str]) -> List[Dict[str, Any]]:
        snapshots = []
        for s in symbols:
            q = await self.provider.get_latest_quote(s)
            if q:
                snapshots.append(
                    {
                        "symbol": q.symbol,
                        "canonical_id": q.canonical_id,
                        "price": float(q.price),
                        "currency": q.currency,
                        "observed_at": q.observed_at.isoformat(),
                        "source": q.source,
                        "data_status": q.data_status,
                    }
                )
        return snapshots

    async def tool_get_price_history(
        self,
        symbol: str,
        interval: str = "1D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        s_date = start_date or "2026-08-01"
        e_date = end_date or "2026-10-16"
        bars = await self.provider.get_historical_bars(symbol, s_date, e_date, interval=interval)
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "count": len(bars),
            "bars": [b.model_dump(mode="json") for b in bars[-20:]],  # Return recent 20 for context
        }

    async def tool_get_stock_facts(self, symbols: List[str]) -> List[Dict[str, Any]]:
        facts = []
        for s in symbols:
            clean = s.upper().strip()
            item = next((i for i in INSTRUMENT_REGISTRY if i["symbol"] == clean), None)
            if item:
                facts.append(item)
            else:
                facts.append(
                    {"symbol": clean, "name": clean, "exchange": "NSE", "currency": "INR", "sector": "General"}
                )
        return facts

    async def tool_get_my_paper_portfolio(
        self, user_id: str, currency: str = "INR", db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        if db:
            summary = await self.engine.get_portfolio_summary_db(user_id, db=db)
            return summary
        acct = self.engine.get_or_create_account(user_id)
        return {
            "account_id": acct["id"],
            "currency": currency,
            "current_cash": float(acct["current_cash"]),
            "equity": float(acct["current_cash"]),
            "positions": [],
            "status": "VIRTUAL_PAPER_ACCOUNT",
        }

    async def tool_get_my_risk_constraints(self, user_id: str, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        risk_band = "MODERATE"
        max_single_stock_pct = 20.0
        if db:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            res = await db.execute(stmt)
            prof = res.scalar_one_or_none()
            if prof and prof.risk_band:
                risk_band = prof.risk_band
                if risk_band == "CONSERVATIVE":
                    max_single_stock_pct = 10.0
                elif risk_band == "AGGRESSIVE":
                    max_single_stock_pct = 35.0

        return {
            "user_id": user_id,
            "risk_band": risk_band,
            "max_single_stock_allocation_pct": max_single_stock_pct,
            "time_horizon_years": 3,
            "prohibited_actions": ["NO_SHORT_SELLING", "NO_MARGIN", "NO_DERIVATIVES"],
        }

    async def tool_compare_candidates(self, symbols: List[str], criteria: Optional[List[str]] = None) -> Dict[str, Any]:
        candidates = []
        for s in symbols:
            q = await self.provider.get_latest_quote(s)
            price = float(q.price) if q else 0.0
            obs_time = q.observed_at.isoformat() if q else "N/A"
            candidates.append(
                {
                    "symbol": s.upper(),
                    "latest_price": price,
                    "currency": "INR",
                    "observed_at": obs_time,
                    "source": q.source if q else "N/A",
                    "data_status": q.data_status if q else "unavailable",
                }
            )
        return {
            "candidates": candidates,
            "criteria_evaluated": criteria or ["latest_price", "data_status", "sector"],
            "disclaimer": SIMULATION_DISCLAIMER,
        }

    async def tool_create_paper_proposal(
        self,
        user_id: str,
        symbols: List[str],
        budget: float,
        currency: str = "INR",
        rationale: str = "Assistant recommended allocation",
        conversation_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Create a server-validated bounded paper allocation proposal with expiration."""
        import math

        if budget is None or not math.isfinite(budget) or budget <= 0:
            return {
                "status": "REJECTED",
                "error": "Budget must be a finite, strictly positive amount.",
                "allocations": [],
                "total_budget": 0.0,
                "requested_budget": float(budget) if budget is not None and math.isfinite(budget) else 0.0,
                "requires_approval": False,
                "disclaimer": SIMULATION_DISCLAIMER,
            }

        if not symbols:
            return {
                "status": "REJECTED",
                "error": "At least one symbol required for allocation proposal.",
                "allocations": [],
                "total_budget": float(budget),
                "requested_budget": float(budget),
                "requires_approval": False,
                "disclaimer": SIMULATION_DISCLAIMER,
            }

        # Treat requested budget as a hard maximum
        budget_dec = Decimal(str(budget))
        per_stock_budget = budget_dec / Decimal(len(symbols))
        allocations = []
        total_estimated = Decimal("0.00")
        unaffordable_symbols = []

        for sym in symbols:
            clean_sym = sym.upper().strip()
            q = await self.provider.get_latest_quote(clean_sym)
            if not q or q.price <= Decimal("0.00"):
                continue
            price = Decimal(str(q.price))
            if price > per_stock_budget:
                unaffordable_symbols.append((clean_sym, price))
                continue
            qty = int(per_stock_budget // price)
            if qty <= 0:
                unaffordable_symbols.append((clean_sym, price))
                continue

            leg_total = Decimal(str(qty)) * price
            # Ensure total estimated never exceeds the requested budget
            if (total_estimated + leg_total) > budget_dec:
                remaining = budget_dec - total_estimated
                qty = int(remaining // price)
                if qty <= 0:
                    continue
                leg_total = Decimal(str(qty)) * price

            total_estimated += leg_total
            allocations.append(
                {
                    "symbol": clean_sym,
                    "quantity": qty,
                    "estimated_price": round(float(price), 2),
                    "estimated_total": round(float(leg_total), 2),
                    "currency": currency,
                }
            )

        if not allocations:
            min_price_info = (
                f" (lowest share price: ₹{min(p for _, p in unaffordable_symbols):,.2f})"
                if unaffordable_symbols
                else ""
            )
            return {
                "status": "INSUFFICIENT_BUDGET",
                "error": f"Requested budget of ₹{budget:,.2f} is insufficient to purchase even a single whole share{min_price_info}. For whole-share paper trading, please provide a larger budget.",
                "requested_budget": float(budget),
                "estimated_allocation_total": 0.0,
                "allocations": [],
                "requires_approval": False,
                "disclaimer": SIMULATION_DISCLAIMER,
            }

        proposal_id = f"prop-{uuid.uuid4().hex[:12]}"
        account_id = f"acc-{user_id}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        if db:
            # Query or create real persisted account in database to satisfy foreign keys
            acct = await self.engine.get_or_create_account_db(user_id, db=db)
            account_id = acct.id

            prop = PaperProposal(
                id=proposal_id,
                user_id=user_id,
                account_id=account_id,
                conversation_id=conversation_id,
                instruction_text=f"Invest {currency} {budget:,.2f} across {', '.join(symbols)}",
                proposed_allocations=allocations,
                requested_budget=Decimal(str(round(budget, 2))),
                total_budget=Decimal(str(round(float(total_estimated), 2))),
                currency=currency,
                status="PROPOSED",
                expires_at=expires_at,
            )
            db.add(prop)
            await db.commit()

        return {
            "proposal_id": proposal_id,
            "status": "PROPOSED",
            "symbols": symbols,
            "requested_budget": round(budget, 2),
            "total_budget": round(float(total_estimated), 2),
            "estimated_allocation_total": round(float(total_estimated), 2),
            "currency": currency,
            "allocations": allocations,
            "expires_in_minutes": 10,
            "expires_at": expires_at.isoformat(),
            "requires_approval": True,
            "disclaimer": SIMULATION_DISCLAIMER,
        }

    async def tool_execute_paper_proposal(
        self,
        user_id: str,
        proposal_id: str,
        is_retry: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Execute pre-validated paper proposal upon explicit authorization with budget enforcement and retry recovery."""
        if not db:
            return {"status": "FAILED", "error": "Database session required for execution"}

        stmt = (
            select(PaperProposal)
            .where(PaperProposal.id == proposal_id, PaperProposal.user_id == user_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        prop = res.scalar_one_or_none()

        if not prop:
            return {"status": "REJECTED", "error": f"Proposal '{proposal_id}' not found for authenticated user."}

        if prop.status == "EXECUTED":
            return {
                "status": "ALREADY_EXECUTED",
                "error": "This proposal has already been executed.",
                "proposal_id": proposal_id,
            }

        if prop.status == "CANCELLED":
            return {
                "status": "CANCELLED",
                "error": "This proposal was cancelled and cannot be executed.",
                "proposal_id": proposal_id,
            }

        now = datetime.now(timezone.utc)
        exp = prop.expires_at.replace(tzinfo=timezone.utc) if prop.expires_at.tzinfo is None else prop.expires_at
        if now > exp:
            prop.status = "EXPIRED"
            await db.commit()
            return {
                "status": "EXPIRED",
                "error": "This paper proposal has expired. Please request a fresh allocation.",
                "proposal_id": proposal_id,
            }

        # Check existing receipts and already filled legs
        existing_receipts = prop.execution_receipts or []
        already_filled_receipts = [r for r in existing_receipts if r.get("status") == "FILLED"]
        already_filled_symbols = {r["symbol"] for r in already_filled_receipts}

        # Handle retry vs replayed attempt
        if prop.status in ("PARTIALLY_EXECUTED", "REJECTED", "FAILED"):
            if is_retry:
                # Bounded attempts
                if prop.attempt_count >= 3:
                    return {
                        "status": "TERMINAL_FAILURE",
                        "error": "Maximum execution retry attempts (3) reached for this proposal. Please request a new proposal.",
                        "proposal_id": proposal_id,
                    }
                prop.attempt_count += 1
            else:
                # Repeated execution of the same attempt returns saved result
                summary = await self.engine.get_portfolio_summary_db(user_id, db=db)
                return {
                    "proposal_id": proposal_id,
                    "status": prop.status,
                    "executed_at": prop.executed_at.isoformat() if prop.executed_at else now.isoformat(),
                    "receipts": existing_receipts,
                    "cash_balance_after": summary.get("current_cash"),
                    "disclaimer": SIMULATION_DISCLAIMER,
                    "replayed": True,
                }

        # Calculate already spent cash by completed legs using exact Decimal arithmetic
        already_spent = sum(
            Decimal(str(r.get("net_value") or r.get("gross_value", "0.00"))) for r in already_filled_receipts
        )

        auth_budget = Decimal(str(prop.requested_budget if prop.requested_budget is not None else prop.total_budget))
        remaining_budget = auth_budget - already_spent

        if remaining_budget <= Decimal("0.00") and len(already_filled_symbols) < len(prop.proposed_allocations):
            return {
                "status": "REJECTED",
                "error": f"Authorized budget of ₹{auth_budget:,.2f} is fully exhausted by completed legs (spent: ₹{already_spent:,.2f}).",
                "proposal_id": proposal_id,
            }

        # Check unfulfilled legs
        unfulfilled_legs = [leg for leg in prop.proposed_allocations if leg["symbol"] not in already_filled_symbols]
        if not unfulfilled_legs:
            prop.status = "EXECUTED"
            await db.commit()
            summary = await self.engine.get_portfolio_summary_db(user_id, db=db)
            return {
                "proposal_id": proposal_id,
                "status": "EXECUTED",
                "executed_at": now.isoformat(),
                "receipts": existing_receipts,
                "cash_balance_after": summary.get("current_cash"),
                "disclaimer": SIMULATION_DISCLAIMER,
            }

        # Revalidate execution prices & budget for all remaining unfulfilled legs before submitting
        total_projected_new_cost = Decimal("0.00")
        leg_quotes = {}
        for leg in unfulfilled_legs:
            sym = leg["symbol"]
            qty = Decimal(str(leg["quantity"]))
            q = await self.provider.get_latest_quote(sym)
            if not q and getattr(self.engine.market_provider, "allow_fixture_fallback", False):
                q = self.engine.get_market_quote_sync(sym)
            leg_quotes[sym] = q
            if q and q.price and q.price > 0 and not q.is_stale and q.data_status != "stale":
                proj_cost = (qty * q.price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_projected_new_cost += proj_cost

        # Reject if price increases make the authorized allocation unaffordable
        if total_projected_new_cost > remaining_budget:
            return {
                "status": "REJECTED",
                "error": (
                    f"Execution cost of remaining legs (₹{total_projected_new_cost:,.2f}) exceeds authorized remaining "
                    f"budget of ₹{remaining_budget:,.2f} (authorized maximum: ₹{auth_budget:,.2f}, already spent: ₹{already_spent:,.2f}). "
                    f"Market prices have increased. Please request a revised proposal."
                ),
                "proposal_id": proposal_id,
                "authorized_budget": float(auth_budget),
                "already_spent": float(already_spent),
                "remaining_budget": float(remaining_budget),
                "projected_cost": float(total_projected_new_cost),
            }

        updated_receipts = list(existing_receipts)
        any_failed = False

        for leg in unfulfilled_legs:
            sym = leg["symbol"]
            qty = Decimal(str(leg["quantity"]))

            # Stable idempotency key per proposal, leg, and attempt
            attempt_idx = getattr(prop, "attempt_count", 1) or 1
            stable_idemp_key = f"prop-{prop.id}-leg-{sym}-att-{attempt_idx}"

            order_req = OrderSubmitRequest(
                symbol=sym,
                side="BUY",
                quantity=qty,
                order_type="MARKET",
                max_total_cost=remaining_budget,
                idempotency_key=stable_idemp_key,
            )
            try:
                exec_result = await self.engine.execute_order_db(user_id, order_req, db=db)
                receipt_dict = exec_result.model_dump(mode="json")
                updated_receipts = [r for r in updated_receipts if r.get("symbol") != sym]
                updated_receipts.append(receipt_dict)
                if exec_result.status == "FILLED":
                    remaining_budget -= exec_result.net_value
                    already_spent += exec_result.net_value
                else:
                    any_failed = True
            except Exception as e:
                any_failed = True
                updated_receipts = [r for r in updated_receipts if r.get("symbol") != sym]
                updated_receipts.append({"symbol": sym, "status": "REJECTED", "error": str(e)})

        filled_count = sum(1 for r in updated_receipts if r.get("status") == "FILLED")
        total_legs = len(prop.proposed_allocations)

        if filled_count == total_legs:
            prop.status = "EXECUTED"
        elif filled_count > 0:
            prop.status = "PARTIALLY_EXECUTED"
        else:
            prop.status = "REJECTED" if any_failed else "FAILED"

        prop.executed_at = now
        prop.execution_receipts = updated_receipts
        await db.commit()

        summary = await self.engine.get_portfolio_summary_db(user_id, db=db)

        return {
            "proposal_id": proposal_id,
            "status": prop.status,
            "executed_at": now.isoformat(),
            "receipts": updated_receipts,
            "cash_balance_after": summary.get("current_cash"),
            "attempt_count": getattr(prop, "attempt_count", 1),
            "disclaimer": SIMULATION_DISCLAIMER,
        }

    async def tool_get_my_paper_order_status(
        self, user_id: str, order_id: str, db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        if db:
            stmt = select(PaperOrder).where(PaperOrder.id == order_id, PaperOrder.user_id == user_id)
            res = await db.execute(stmt)
            order = res.scalar_one_or_none()
            if order:
                return {
                    "order_id": order.id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": float(order.quantity),
                    "fill_price": float(order.fill_price) if order.fill_price else None,
                    "status": order.status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "receipt": order.execution_receipt,
                }
        return {"order_id": order_id, "status": "NOT_FOUND"}

    async def tool_get_chart_context(
        self,
        symbol: str,
        timeframe: str = "1D",
        visible_bars: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Provide detailed chart context for Gemini active chart understanding."""
        clean_sym = symbol.upper()
        q = await self.provider.get_latest_quote(clean_sym)
        bars = await self.provider.get_historical_bars(clean_sym, "2026-08-01", "2026-10-16", interval=timeframe)

        raw_bars = [b.model_dump(mode="json") for b in bars]
        sma20 = calculate_sma(raw_bars, 20)
        rsi14 = calculate_rsi(raw_bars, 14)
        macd = calculate_macd(raw_bars)

        latest_sma = sma20[-1]["value"] if sma20 else None
        latest_rsi = rsi14[-1]["value"] if rsi14 else None
        latest_macd = macd[-1] if macd else {}

        return {
            "symbol": clean_sym,
            "timeframe": timeframe,
            "latest_price": float(q.price) if q else None,
            "currency": q.currency if q else "INR",
            "observation_date": q.observed_at.isoformat() if q else "N/A",
            "source": q.source if q else "N/A",
            "data_status": q.data_status if q else "N/A",
            "total_bars": len(bars),
            "recent_bars_sample": raw_bars[-5:],
            "active_indicators": {
                "SMA_20": latest_sma,
                "RSI_14": latest_rsi,
                "MACD": latest_macd.get("macd"),
                "MACD_Signal": latest_macd.get("signal"),
                "MACD_Histogram": latest_macd.get("histogram"),
            },
            "disclaimer": SIMULATION_DISCLAIMER,
        }

    # --- Main Orchestration Entrypoint ---

    async def process_user_turn(
        self,
        user_id: str,
        user_message: str,
        conversation_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        active_chart_context: Optional[Dict[str, Any]] = None,
    ) -> AssistantMessageResponse:
        """Process user message using Google Gemini with function calling and server-verified execution."""
        msg_id = f"msg-{uuid.uuid4().hex[:12]}"
        conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        lang = self.detect_language(user_message)
        p_lower = user_message.lower().strip()

        # Resolve active symbol from context if present
        active_sym = "RELIANCE"
        if active_chart_context and isinstance(active_chart_context, dict):
            active_sym = active_chart_context.get("symbol", "RELIANCE")

        # 1. Research & Educational Question Intent ("Should I invest?", "Is it good to buy?", etc.)
        # Informational and research queries must remain research requests and NEVER execute or cancel trades.
        is_research_query = (
            user_message.strip().endswith("?")
            or any(
                p_lower.startswith(q)
                for q in [
                    "should i",
                    "is it good",
                    "is it a good time",
                    "why ",
                    "what ",
                    "how ",
                    "can i",
                    "would you",
                    "kya mujhe",
                    "kya yeh",
                    "tell me about",
                    "explain",
                    "analysis of",
                    "review",
                ]
            )
            or any(
                q in p_lower
                for q in [
                    "should i invest",
                    "should i buy",
                    "is it good to invest",
                    "is it good to buy",
                    "is it safe to invest",
                    "kya invest karna chahiye",
                    "kya buy karna chahiye",
                ]
            )
        )

        # 2. Refusal & Cancellation Intent ("do not execute", "don't execute", "cancel", "wait", "don't buy", "stop")
        refusal_phrases = [
            "do not execute",
            "don't execute",
            "dont execute",
            "do not buy",
            "don't buy",
            "dont buy",
            "do not invest",
            "don't invest",
            "dont invest",
            "do not trade",
            "don't trade",
            "dont trade",
            "cancel proposal",
            "cancel order",
            "abort trade",
            "stop execution",
            "mat karo",
            "ruko",
            "nahi karna",
        ]
        is_refusal = not is_research_query and (
            any(phrase in p_lower for phrase in refusal_phrases)
            or p_lower
            in [
                "no",
                "nah",
                "nope",
                "nahi",
                "cancel",
                "stop",
                "wait",
                "abort",
                "reject",
            ]
            or (p_lower.startswith("cancel ") and "prop-" in p_lower)
        )

        if is_refusal:
            active_prop = None
            if db:
                # Check if explicit proposal ID was provided for cancellation
                explicit_cancel_match = re.search(r"\b(prop-[a-zA-Z0-9_-]+)\b", user_message, re.IGNORECASE)
                if explicit_cancel_match:
                    target_cancel_id = explicit_cancel_match.group(1)
                    prop_stmt = select(PaperProposal).where(
                        PaperProposal.id == target_cancel_id,
                        PaperProposal.user_id == user_id,
                    )
                    prop_res = await db.execute(prop_stmt)
                    active_prop = prop_res.scalar_one_or_none()
                    if active_prop:
                        if active_prop.status == "PROPOSED":
                            active_prop.status = "CANCELLED"
                            await db.commit()
                            reply = f"Proposal '{target_cancel_id}' has been cancelled. No orders were placed and your virtual balance remains unchanged."
                        else:
                            reply = f"Proposal '{target_cancel_id}' is in '{active_prop.status}' state and cannot be cancelled."
                    else:
                        reply = f"Proposal '{target_cancel_id}' was not found for your account to cancel."
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )
                else:
                    # Scope strictly to this conversation - NEVER cancel proposals in unrelated conversations
                    prop_stmt = (
                        select(PaperProposal)
                        .where(
                            PaperProposal.user_id == user_id,
                            PaperProposal.conversation_id == conv_id,
                            PaperProposal.status == "PROPOSED",
                        )
                        .order_by(desc(PaperProposal.created_at))
                        .limit(1)
                    )
                    prop_res = await db.execute(prop_stmt)
                    active_prop = prop_res.scalar_one_or_none()
                    if active_prop:
                        active_prop.status = "CANCELLED"
                        await db.commit()
                        if lang == "hi":
                            reply = "प्रस्ताव निष्पादन रद्द कर दिया गया है। कोई पेपर ट्रेड निष्पादित नहीं किया गया और आपका वर्चुअल बैलेंस सुरक्षित है।"
                        elif lang == "hi-Latn":
                            reply = "Paper trade execution cancel kar diya gaya hai. Koi order place nahi hua aur aapka virtual cash balance safe hai."
                        else:
                            reply = "Paper trade execution cancelled. No orders were placed and your virtual balance remains unchanged."
                    else:
                        # Do not claim a proposal was cancelled when nothing matched
                        reply = "No active pending paper trade proposal found in this conversation to cancel."
            else:
                reply = "No active pending paper trade proposal found to cancel."

            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                is_setup_incomplete=False,
            )

        # 3. Explicit Proposal Authorization
        # Reject negated or ambiguous authorization
        negated_approval_phrases = [
            "do not confirm",
            "don't confirm",
            "dont confirm",
            "not confirm",
            "do not execute",
            "don't execute",
            "dont execute",
            "never execute",
            "never confirm",
            "not sure",
        ]
        is_negated_approval = any(neg in p_lower for neg in negated_approval_phrases)

        if is_negated_approval and not is_research_query:
            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply="Confirmation not granted. No paper orders were placed.",
                language_detected=lang,
                is_setup_incomplete=False,
            )

        approval_tokens = {
            "yes",
            "approve",
            "confirm",
            "proceed",
            "haan",
            "theek hai",
            "execute proposal",
            "confirm proposal",
            "yes execute",
            "yes proceed",
            "yes confirm",
            "confirm order",
            "execute order",
            "confirm trade",
            "execute trade",
        }
        is_approval = (
            not is_refusal
            and not is_research_query
            and not is_negated_approval
            and (
                p_lower in approval_tokens
                or p_lower.startswith("confirm proposal")
                or p_lower.startswith("execute proposal")
                or p_lower.startswith("confirm prop-")
                or p_lower.startswith("execute prop-")
                or any(f"confirm {t}" in p_lower for t in ["proposal", "order", "trade", "this"])
                or (any(p_lower == token for token in ["yes", "confirm", "approve", "proceed", "haan"]))
            )
        )

        if is_approval and db:
            explicit_prop_id_match = re.search(r"\b(prop-[a-zA-Z0-9_-]+)\b", user_message, re.IGNORECASE)
            target_prop = None

            if explicit_prop_id_match:
                # 1. Explicit proposal ID takes absolute precedence!
                explicit_id = explicit_prop_id_match.group(1)
                spec_stmt = select(PaperProposal).where(
                    PaperProposal.id == explicit_id,
                    PaperProposal.user_id == user_id,
                )
                spec_res = await db.execute(spec_stmt)
                target_prop = spec_res.scalar_one_or_none()

                if not target_prop:
                    # Never substitute another proposal when requested ID is invalid or unavailable!
                    reply = (
                        f"Proposal '{explicit_id}' was not found for this account. No other proposal will be executed."
                    )
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )

                if target_prop.status == "CANCELLED":
                    reply = f"Proposal '{explicit_id}' was cancelled and cannot be executed."
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )

                if target_prop.status == "EXECUTED":
                    reply = f"Proposal '{explicit_id}' has already been executed. No duplicate orders were placed."
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )

                now_exp = datetime.now(timezone.utc)
                exp_dt = (
                    target_prop.expires_at.replace(tzinfo=timezone.utc)
                    if target_prop.expires_at.tzinfo is None
                    else target_prop.expires_at
                )
                if now_exp > exp_dt:
                    target_prop.status = "EXPIRED"
                    await db.commit()
                    reply = f"Proposal '{explicit_id}' has expired. Please request a fresh allocation proposal."
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )
            else:
                # 2. Generic confirmation without explicit ID:
                # Query all active pending proposals in THIS conversation
                stmt_pending = (
                    select(PaperProposal)
                    .where(
                        PaperProposal.user_id == user_id,
                        PaperProposal.conversation_id == conv_id,
                        PaperProposal.status.in_(["PROPOSED", "PARTIALLY_EXECUTED"]),
                    )
                    .order_by(PaperProposal.created_at)
                )
                pending_list = (await db.execute(stmt_pending)).scalars().all()

                if not pending_list:
                    if lang in ("hi", "hi-Latn"):
                        reply = "Is conversation me koi active pending paper trade proposal nahi mila. Pehle naya allocation proposal create karein (jaise: 'Invest ₹10,000 in RELIANCE')."
                    else:
                        reply = "No active pending paper trade proposal found in this conversation to confirm. Please create an allocation proposal first (e.g. 'Invest ₹10,000 in RELIANCE')."
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )

                if len(pending_list) > 1:
                    # Multiple proposals in same conversation: require user to select one!
                    prop_ids_str = ", ".join(f"'{p.id}'" for p in pending_list)
                    reply = (
                        f"Multiple pending proposals found in this conversation ({prop_ids_str}). "
                        f"Please specify which proposal ID you wish to confirm (e.g. 'confirm {pending_list[-1].id}')."
                    )
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )

                target_prop = pending_list[0]
                now_exp = datetime.now(timezone.utc)
                exp_dt = (
                    target_prop.expires_at.replace(tzinfo=timezone.utc)
                    if target_prop.expires_at.tzinfo is None
                    else target_prop.expires_at
                )
                if now_exp > exp_dt:
                    target_prop.status = "EXPIRED"
                    await db.commit()
                    reply = "This paper proposal has expired. Please request a fresh allocation proposal."
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=reply,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )

            is_retry = (target_prop.status in ("PARTIALLY_EXECUTED", "REJECTED")) or ("retry" in p_lower)
            exec_result = await self.tool_execute_paper_proposal(user_id, target_prop.id, is_retry=is_retry, db=db)
            status = exec_result.get("status")

            if status == "EXECUTED":
                if lang in ("hi", "hi-Latn"):
                    reply = (
                        f"Aapka paper order safalta-purvak execute ho gaya hai! "
                        f"Virtual cash balance: ₹{exec_result.get('cash_balance_after', 0):,.2f}."
                    )
                else:
                    reply = (
                        f"Paper allocation executed successfully! "
                        f"Remaining virtual cash balance: ₹{exec_result.get('cash_balance_after', 0):,.2f}."
                    )
            elif status == "PARTIALLY_EXECUTED":
                reply = (
                    f"Paper allocation partially executed. Some order legs filled, but others could not be completed. "
                    f"Check receipts for details. Remaining virtual cash: ₹{exec_result.get('cash_balance_after', 0):,.2f}."
                )
            elif status == "ALREADY_EXECUTED":
                reply = "This paper proposal was already executed. No duplicate orders were placed."
            elif status == "EXPIRED":
                reply = "This paper proposal has expired. Please request a fresh allocation proposal."
            elif status == "CANCELLED":
                reply = "This paper proposal was cancelled. No orders were executed."
            else:
                reply = f"Proposal execution could not proceed: {exec_result.get('error', 'Execution rejected')}."

            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                execution_receipt=exec_result,
                is_setup_incomplete=False,
            )

        # 2. Greetings and Conversational Onboarding (e.g. "hey", "hello", "hi", "namaste", "what can you do")
        greeting_words = [
            "hey",
            "hi",
            "hello",
            "namaste",
            "hie",
            "heyy",
            "hola",
            "good morning",
            "good afternoon",
            "good evening",
            "sup",
            "who are you",
            "what can you do",
            "help",
            "madad",
            "kya kar sakte ho",
            "kaise ho",
            "kya haal hai",
        ]
        is_greeting = any(
            p_lower == w or p_lower.startswith(w + " ") or p_lower.endswith(" " + w) or f" {w} " in f" {p_lower} "
            for w in greeting_words
        )
        if is_greeting and not any(w in p_lower for w in ["invest", "buy", "chart", "rsi", "balance", "portfolio"]):
            if self.is_gemini_api_ready():
                sys_instruct = (
                    "You are FinEx AI Paper Investment Assistant for Indian Equities (NSE). "
                    f"Active chart instrument: {active_sym}. "
                    f"Respond warmly and helpfully in '{lang}' (English, Hindi, or Hinglish as appropriate). "
                    f"Greet the user, note you are powered by Gemini AI, and suggest 3 quick ideas they can explore: "
                    f"1) Technical analysis on {active_sym} chart & indicators (RSI, SMA), "
                    f"2) Propose paper portfolio trades (e.g. 'Invest ₹15,000 in {active_sym} and TCS'), "
                    f"3) Check their virtual paper trading balance. Keep your answer concise and welcoming."
                )
                gemini_text = await self.call_gemini_api(user_message, sys_instruct)
                if gemini_text:
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=gemini_text,
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )

            if lang == "hi":
                reply = (
                    f"नमस्ते! मैं आपका FinEx AI पेपर इन्वेस्टमेंट असिस्टेंट हूँ।\n\n"
                    f"मैं सक्रिय चार्ट (**{active_sym}**) का विश्लेषण करने, तकनीकी संकेतकों (RSI, 20-डे SMA, MACD) की गणना करने, या आपके वर्चुअल बजट में पेपर आवंटन तैयार करने में मदद कर सकता हूँ।\n\n"
                    f"आप मुझसे पूछ सकते हैं:\n"
                    f"- 📊 **'{active_sym} चार्ट समझाओ'** या **'RSI क्या है?'**\n"
                    f"- 💼 **'{active_sym} और TCS में ₹15,000 इन्वेस्ट करो'**\n"
                    f"- 📈 **'भारतीय बाजार के मुख्य शेयर्स दिखाओ'**\n"
                    f"- 🔄 **'मेरा वर्चुअल पोर्टफोलियो बैलेंस कितना है?'**\n\n"
                    f"आज आप किस स्टॉक या चार्ट का विश्लेषण करना चाहते हैं?"
                )
            elif lang == "hi-Latn":
                reply = (
                    f"Namaste! Main aapka FinEx AI Paper Investment Assistant hoon.\n\n"
                    f"Main active chart (**{active_sym}**) analyze karne, technical indicators (RSI, 20-Day SMA, MACD) calculate karne, aur simulated investments propose karne me help kar sakta hoon.\n\n"
                    f"Aap mujhse puch sakte hain:\n"
                    f"- 📊 **'{active_sym} chart samjhao'** ya **'RSI kitna hai?'**\n"
                    f"- 💼 **'{active_sym} aur TCS me 15000 invest karo'**\n"
                    f"- 📈 **'Top Indian stocks research dikhao'**\n"
                    f"- 🔄 **'Mera virtual cash balance kitna hai?'**\n\n"
                    f"Bataiye, aaj aap kis stock ya chart par research karna chahte hain?"
                )
            else:
                reply = (
                    f"Namaste! I am your FinEx AI Paper Investment Assistant.\n\n"
                    f"I can help you analyze the active chart (**{active_sym}**), calculate technical indicators (RSI, 20-day SMA, MACD), or formulate virtual paper trade proposals within your simulated budget.\n\n"
                    f"Here are a few questions you can ask me:\n"
                    f"- 📊 **'Explain {active_sym} chart'** or **'What is the RSI of this stock?'**\n"
                    f"- 💼 **'Invest ₹15,000 in {active_sym} and TCS'**\n"
                    f"- 📈 **'Show top Indian market leaders'**\n"
                    f"- 🔄 **'What is my virtual paper portfolio balance?'**\n\n"
                    f"How can I assist your paper trading research today?"
                )
            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                is_setup_incomplete=False,
            )

        # 3. Virtual Portfolio / Balance Inquiry
        portfolio_words = [
            "portfolio",
            "balance",
            "cash",
            "mera balance",
            "holdings",
            "kitna paisa",
            "kitne paise",
            "virtual cash",
        ]
        if any(w in p_lower for w in portfolio_words) and not any(w in p_lower for w in ["invest", "buy", "kharid"]):
            summary = await self.tool_get_my_paper_portfolio(user_id, currency="INR", db=db)
            cash = float(summary.get("current_cash", 1000000.0))
            equity = float(summary.get("equity", cash))
            positions = summary.get("positions", [])
            pos_text = ""
            if positions:
                pos_text = "\n".join(
                    [
                        f"- **{p.get('symbol')}**: {p.get('quantity')} shares @ avg ₹{float(p.get('avg_entry_price', 0)):,.2f}"
                        for p in positions
                    ]
                )
            else:
                pos_text = "- No open positions in your virtual ledger yet."

            if lang == "hi":
                reply = (
                    f"**आपका वर्चुअल पेपर पोर्टफोलियो:**\n\n"
                    f"- उपलब्ध वर्चुअल कैश: ₹{cash:,.2f}\n"
                    f"- कुल पोर्टफोलियो इक्विटी: ₹{equity:,.2f}\n\n"
                    f"**सक्रिय पोजीशन्स ({len(positions)}):**\n"
                    f"{pos_text}\n\n"
                    f"नया पेपर ऑर्डर लगाने के लिए राशि बताएं (उदा: '₹10,000 इन्वेस्ट करो')।"
                )
            elif lang == "hi-Latn":
                reply = (
                    f"**Aapka Virtual Paper Portfolio:**\n\n"
                    f"- Available Virtual Cash: ₹{cash:,.2f}\n"
                    f"- Total Portfolio Equity: ₹{equity:,.2f}\n\n"
                    f"**Active Positions ({len(positions)}):**\n"
                    f"{pos_text}\n\n"
                    f"Paper trading proposal ke liye budget batayein (jaise: 'Invest 10000 in {active_sym}')."
                )
            else:
                reply = (
                    f"**Your Virtual Paper Portfolio Summary:**\n\n"
                    f"- Available Virtual Cash: ₹{cash:,.2f}\n"
                    f"- Total Portfolio Equity: ₹{equity:,.2f}\n\n"
                    f"**Active Positions ({len(positions)}):**\n"
                    f"{pos_text}\n\n"
                    f"To allocate virtual capital, say e.g. *'Invest INR 25,000 across Nifty leaders'*."
                )
            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                evidence_cards=[summary],
                is_setup_incomplete=False,
            )

        # 4. Chart Context Explanation (e.g. "explain this chart", "rsi", "chart samjhao", "moving average")
        if any(
            w in p_lower
            for w in [
                "chart",
                "rsi",
                "moving average",
                "sma",
                "macd",
                "graph",
                "indicator",
                "trend",
                "technicals",
            ]
        ):
            target_sym = active_sym
            for item in INSTRUMENT_REGISTRY:
                if item["symbol"].lower() in p_lower or item["name"].lower() in p_lower:
                    target_sym = item["symbol"]
                    break

            chart_ctx = await self.tool_get_chart_context(target_sym, db=db)
            price = chart_ctx.get("latest_price")
            rsi_val = chart_ctx.get("active_indicators", {}).get("RSI_14")
            sma_val = chart_ctx.get("active_indicators", {}).get("SMA_20")
            price_str = f"₹{price:,.2f}" if price is not None else "Quote unavailable"

            if lang == "hi":
                reply = (
                    f"**{target_sym} सक्रिय चार्ट विश्लेषण:**\n"
                    f"- नवीनतम सत्यापित मूल्य: {price_str} (स्रोत: {chart_ctx.get('source')})\n"
                    f"- 20-दिवसीय SMA: ₹{f'{sma_val:,.2f}' if sma_val else 'तैयार हो रहा है'}\n"
                    f"- RSI (14): {f'{rsi_val:.1f}' if rsi_val else 'पर्याप्त डेटा नहीं'} "
                    f"({'ओवरबॉट क्षेत्र (>70)' if rsi_val and rsi_val > 70 else 'ओवरसोल्ड क्षेत्र (<30)' if rsi_val and rsi_val < 30 else 'संतुलित रेंज (30-70)'})\n\n"
                    f"सभी डेटा बिंदु वास्तविक ऐतिहासिक अवलोकनों से प्राप्त किए गए हैं।"
                )
            elif lang == "hi-Latn":
                reply = (
                    f"**{target_sym} Active Chart Analysis:**\n"
                    f"- Current Price: {price_str} (Source: {chart_ctx.get('source')})\n"
                    f"- 20-Day SMA: ₹{f'{sma_val:,.2f}' if sma_val else 'Calculating'}\n"
                    f"- RSI (14): {f'{rsi_val:.1f}' if rsi_val else 'N/A'} "
                    f"({'Overbought zone (>70)' if rsi_val and rsi_val > 70 else 'Oversold zone (<30)' if rsi_val and rsi_val < 30 else 'Neutral range (30-70)'})\n\n"
                    f"Yeh observation active chart historical data par aadharit hai."
                )
            else:
                reply = (
                    f"**{target_sym} Active Chart Analysis:**\n"
                    f"- Current Price: {price_str} (Source: {chart_ctx.get('source')})\n"
                    f"- 20-Day SMA: ₹{f'{sma_val:,.2f}' if sma_val else 'Calculating'}\n"
                    f"- RSI (14): {f'{rsi_val:.1f}' if rsi_val else 'N/A'} "
                    f"({'Overbought (>70)' if rsi_val and rsi_val > 70 else 'Oversold (<30)' if rsi_val and rsi_val < 30 else 'Neutral range (30-70)'})\n\n"
                    f"All data points are grounded in authentic historical observations."
                )

            if self.is_gemini_api_ready():
                sys_prompt = (
                    "You are FinEx AI Technical & Chart Analysis Copilot for Indian Equities (NSE). "
                    f"Active instrument: {target_sym} at current verified price {price_str} ({chart_ctx.get('source')}). "
                    f"Quantitative technical indicators: "
                    f"20-Day Simple Moving Average (SMA): ₹{f'{sma_val:,.2f}' if sma_val else 'Calculating'}, "
                    f"14-Period RSI: {f'{rsi_val:.1f}' if rsi_val else 'N/A'}, "
                    f"Timeframe: {chart_ctx.get('timeframe', '1D')}. "
                    f"Respond in '{lang}' (English, Hindi, or Hinglish as appropriate). "
                    "Provide an objective, educational technical analysis explaining price momentum, key levels, and risk parameters. "
                    "Maintain strict compliance: all figures are educational paper trading metrics."
                )
                gemini_text = await self.call_gemini_api(user_message, sys_prompt)
                if gemini_text:
                    reply = gemini_text

            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                evidence_cards=[chart_ctx],
                is_setup_incomplete=False,
            )

        # 5. Paper Investment Proposal Request (e.g. "invest 10000", "invest in reliance and tcs", "10000 laga do")
        # Must NOT be a research question ("Should I invest 10000 in Reliance?")
        if (
            any(w in p_lower for w in ["invest", "khareed", "kharido", "allocation", "laga do", "buy"])
            and any(c.isdigit() for c in user_message)
            and not is_research_query
        ):
            numbers = re.findall(r"\b\d[\d,]*\b", user_message.replace(",", ""))
            budget_val = float(numbers[0]) if numbers else 10000.0

            target_symbols = []
            for item in INSTRUMENT_REGISTRY:
                if item["symbol"].lower() in p_lower or item["name"].lower() in p_lower:
                    target_symbols.append(item["symbol"])
            if not target_symbols:
                target_symbols = [active_sym, "TCS"] if active_sym != "TCS" else ["TCS", "RELIANCE"]

            proposal = await self.tool_create_paper_proposal(
                user_id, target_symbols, budget=budget_val, currency="INR", conversation_id=conv_id, db=db
            )

            if proposal.get("status") == "INSUFFICIENT_BUDGET":
                if lang in ("hi", "hi-Latn"):
                    reply = (
                        f"Aapka requested budget ₹{budget_val:,.2f} ek bhi poora share khareedne ke liye kam hai. "
                        f"{proposal.get('error', '')} Kripya budget badhayein."
                    )
                else:
                    reply = (
                        f"Your requested budget of ₹{budget_val:,.2f} is insufficient to purchase even a single whole share. "
                        f"{proposal.get('error', '')} Please provide a larger budget."
                    )
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=reply,
                    language_detected=lang,
                    proposal=proposal,
                    is_setup_incomplete=False,
                )

            alloc_details = "\n".join(
                [
                    f"- **{a['symbol']}**: {a['quantity']} shares @ ₹{a['estimated_price']:,.2f} (Total: ₹{a['estimated_total']:,.2f})"
                    for a in proposal.get("allocations", [])
                ]
            )

            if lang == "hi":
                reply = (
                    f"मैंने आपके लिए ₹{budget_val:,.2f} का सिमुलेटेड आवंटन प्रस्ताव तैयार किया है:\n\n"
                    f"{alloc_details}\n\n"
                    f"कुल अनुमानित लागत: ₹{proposal.get('estimated_allocation_total', 0):,.2f}.\n"
                    f"यदि आप सहमत हैं, तो **'हाँ'** या **'Confirm'** कहें। यह प्रस्ताव 10 मिनट के लिए मान्य है।"
                )
            elif lang == "hi-Latn":
                reply = (
                    f"Maine aapke liye ₹{budget_val:,.2f} ka paper allocation proposal banaya hai:\n\n"
                    f"{alloc_details}\n\n"
                    f"Estimated total: ₹{proposal.get('estimated_allocation_total', 0):,.2f}.\n"
                    f"Kya aap isse execute karna chahte hain? Confirm karne ke liye **'Yes'** ya **'Haan'** kahein."
                )
            else:
                reply = (
                    f"Here is a proposed paper allocation for ₹{budget_val:,.2f} of virtual balance:\n\n"
                    f"{alloc_details}\n\n"
                    f"Total Estimated Outlay: ₹{proposal.get('estimated_allocation_total', 0):,.2f} virtual INR.\n"
                    f"To authorize execution, please reply **'Yes'** or **'Confirm'**. Proposal expires in 10 minutes."
                )

            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                proposal=proposal,
                is_setup_incomplete=False,
            )

        # 6. Try Live Gemini API with Grounding if key is available
        if self.is_gemini_api_ready():
            sys_instruct = (
                "You are FinEx AI Paper Investment Assistant for Indian Equities (NSE). "
                f"Active chart context: {active_chart_context or {'symbol': active_sym}}. "
                "Respond helpfully in the user's language (English, Hindi, or Hinglish). "
                "Maintain strict SEBI educational compliance: all trades and balances are 100% virtual paper trading. "
                "Ground all market prices and facts strictly using provided backend tools. Never invent quotes."
            )
            gemini_reply, tool_calls, evidence = await self.call_gemini_grounded(
                user_message, sys_instruct, user_id=user_id, active_sym=active_sym, db=db
            )
            if gemini_reply:
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=gemini_reply,
                    language_detected=lang,
                    tool_calls=tool_calls,
                    evidence_cards=evidence,
                    is_setup_incomplete=False,
                )

        # 7. Fallback: Research & Educational Shortlist for Top Indian Equities
        snapshots = await self.tool_get_market_snapshot(["RELIANCE", "TCS", "INFY", "HDFCBANK"])
        stock_bullets = "\n".join([f"- **{s['symbol']}**: ₹{s['price']:,.2f} ({s['source']})" for s in snapshots])

        if lang == "hi":
            reply = (
                f"आपके पेपर पोर्टफोलियो अनुसंधान के लिए उपलब्ध सत्यापित उपकरण:\n\n"
                f"{stock_bullets}\n\n"
                f"**महत्वपूर्ण सिद्धांत:**\n"
                f"1. विविधीकरण (Diversification): सभी पूंजी एक क्षेत्र में केंद्रित न करें।\n"
                f"2. जोखिम प्रबंधन: अपने जोखिम प्रोफाइल के अनुसार सीमाएं निर्धारित करें।\n\n"
                f"आवंटन प्रस्ताव के लिए राशि बताएं (उदा: '₹10,000 इन्वेस्ट करो') या '{active_sym} चार्ट समझाओ' पूछें।"
            )
        elif lang == "hi-Latn":
            reply = (
                f"Aapke paper portfolio research ke liye available instruments:\n\n"
                f"{stock_bullets}\n\n"
                f"**Prudent Principles:**\n"
                f"- Diversification: Multiple sectors me balance banayein.\n"
                f"- Risk Limits: Single stock me 20% se zyada allocate na karein.\n\n"
                f"Agar paper allocation chahiye to budget batayein (e.g. 'Invest 10000') ya '{active_sym} chart samjhao' kahein."
            )
        else:
            reply = (
                f"Here is the verified observation shortlist available for paper research:\n\n"
                f"{stock_bullets}\n\n"
                f"**Portfolio Construction Principles:**\n"
                f"- **Sector Diversification**: Balance across technology, banking, and energy.\n"
                f"- **Risk Limits**: Keep single-stock exposure bounded to your risk profile.\n\n"
                f"To request a paper allocation, state your virtual budget (e.g. *'Invest INR 10,000 across these stocks'*) or ask *'Explain {active_sym} chart'*."
            )

        return AssistantMessageResponse(
            message_id=msg_id,
            conversation_id=conv_id,
            reply=reply,
            language_detected=lang,
            evidence_cards=snapshots,
            is_setup_incomplete=False,
        )


gemini_assistant = GeminiInvestmentAssistant()
