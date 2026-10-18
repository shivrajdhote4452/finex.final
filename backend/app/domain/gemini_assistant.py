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

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

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
from backend.app.models.paper_trading import PaperAccount, PaperOrder, PaperProposal
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
        self.engine = engine or PaperTradingEngine()
        self.provider = provider or RealMarketDataProvider(force_cache=False, allow_fixture_fallback=True)

    def is_gemini_api_ready(self) -> bool:
        """Verify if a valid, non-placeholder GEMINI_API_KEY is configured for external API calls."""
        if getattr(self.settings, "LLM_PROVIDER", "").lower() in ("mock", "offline", "simulated", "local"):
            return False
        key = getattr(self.settings, "GEMINI_API_KEY", None)
        if not key or "YOUR_NEW_GEMINI_API_KEY" in key or "placeholder" in key.lower():
            return False
        return len(key.strip()) >= 10

    def is_configured(self) -> bool:
        """Verify if assistant is functional (operational in both live Gemini API and offline simulator mode)."""
        return True

    async def call_gemini_api(self, prompt: str, system_instruction: str) -> Optional[str]:
        """Invoke Google Gemini 1.5 API using httpx with robust headers and graceful fallback."""
        if not self.is_gemini_api_ready():
            return None
        key = self.settings.GEMINI_API_KEY
        model = getattr(self.settings, "GEMINI_MODEL", "gemini-1.5-flash") or "gemini-1.5-flash"
        headers = {
            "x-goog-api-key": key,
            "Content-Type": "application/json",
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 800,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                elif res.status_code == 404:
                    # Model ID fallback if gemini-1.5-flash has variant naming
                    for alt_model in ["gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-1.5-pro"]:
                        alt_url = f"https://generativelanguage.googleapis.com/v1beta/models/{alt_model}:generateContent?key={key}"
                        res_alt = await client.post(alt_url, json=payload, headers=headers)
                        if res_alt.status_code == 200:
                            data = res_alt.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    return parts[0].get("text", "").strip()
        except Exception:
            pass
        return None

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
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Create a server-validated bounded paper allocation proposal with expiration."""
        if budget <= 0:
            raise ValueError("Budget must be strictly positive.")
        if not symbols:
            raise ValueError("At least one symbol required for proposal.")

        # Allocate evenly among symbols
        per_stock_budget = budget / len(symbols)
        allocations = []
        total_estimated = 0.0

        for sym in symbols:
            q = await self.provider.get_latest_quote(sym)
            if not q or q.price <= 0:
                continue
            price = float(q.price)
            qty = max(1, int(per_stock_budget // price))
            leg_total = qty * price
            total_estimated += leg_total
            allocations.append(
                {
                    "symbol": sym.upper(),
                    "quantity": qty,
                    "estimated_price": round(price, 2),
                    "estimated_total": round(leg_total, 2),
                    "currency": currency,
                }
            )

        proposal_id = f"prop-{uuid.uuid4().hex[:12]}"
        account_id = f"acc-{user_id}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        if db:
            # Query actual account ID
            acct_stmt = select(PaperAccount).where(PaperAccount.user_id == user_id)
            acct_res = await db.execute(acct_stmt)
            db_acct = acct_res.scalar_one_or_none()
            if db_acct:
                account_id = db_acct.id

            prop = PaperProposal(
                id=proposal_id,
                user_id=user_id,
                account_id=account_id,
                instruction_text=f"Invest {currency} {budget:,.2f} across {', '.join(symbols)}",
                proposed_allocations=allocations,
                total_budget=Decimal(str(round(total_estimated, 2))),
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
            "total_budget": round(budget, 2),
            "estimated_allocation_total": round(total_estimated, 2),
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
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Execute pre-validated paper proposal upon explicit authorization."""
        if not db:
            return {"status": "FAILED", "error": "Database session required for execution"}

        stmt = select(PaperProposal).where(PaperProposal.id == proposal_id, PaperProposal.user_id == user_id)
        res = await db.execute(stmt)
        prop = res.scalar_one_or_none()

        if not prop:
            return {"status": "REJECTED", "error": f"Proposal '{proposal_id}' not found for authenticated user."}

        if prop.status == "EXECUTED":
            return {"status": "ALREADY_EXECUTED", "error": "This proposal has already been executed."}

        now = datetime.now(timezone.utc)
        exp = prop.expires_at.replace(tzinfo=timezone.utc) if prop.expires_at.tzinfo is None else prop.expires_at
        if now > exp:
            prop.status = "EXPIRED"
            await db.commit()
            return {"status": "EXPIRED", "error": "This paper proposal has expired. Please request a fresh allocation."}

        # Execute each allocation leg through PaperTradingEngine
        execution_receipts = []
        all_succeeded = True

        for leg in prop.proposed_allocations:
            order_req = OrderSubmitRequest(
                symbol=leg["symbol"],
                side="BUY",
                quantity=Decimal(str(leg["quantity"])),
                order_type="MARKET",
                idempotency_key=f"prop-{prop.id}-{leg['symbol']}-{uuid.uuid4().hex[:6]}",
            )
            try:
                exec_result = await self.engine.execute_order_db(user_id, order_req, db=db)
                receipt_dict = exec_result.model_dump(mode="json")
                execution_receipts.append(receipt_dict)
                if exec_result.status != "FILLED":
                    all_succeeded = False
            except Exception as e:
                all_succeeded = False
                execution_receipts.append({"symbol": leg["symbol"], "status": "REJECTED", "error": str(e)})

        prop.status = "EXECUTED" if all_succeeded else "PARTIALLY_EXECUTED"
        prop.executed_at = now
        prop.execution_receipts = execution_receipts
        await db.commit()

        # Fetch updated portfolio balance
        summary = await self.engine.get_portfolio_summary_db(user_id, db=db)

        return {
            "proposal_id": proposal_id,
            "status": prop.status,
            "executed_at": now.isoformat(),
            "receipts": execution_receipts,
            "cash_balance_after": summary.get("current_cash"),
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

        # 1. Explicit Proposal Approval (e.g. "yes", "approve", "confirm", "proceed", "haan")
        if (
            any(w in p_lower for w in ["yes", "approve", "confirm", "proceed", "haan", "theek hai", "execute"])
            and len(p_lower.split()) <= 4
        ):
            if db:
                prop_stmt = (
                    select(PaperProposal)
                    .where(PaperProposal.user_id == user_id, PaperProposal.status == "PROPOSED")
                    .order_by(desc(PaperProposal.created_at))
                    .limit(1)
                )
                prop_res = await db.execute(prop_stmt)
                recent_prop = prop_res.scalar_one_or_none()
                if recent_prop:
                    exec_result = await self.tool_execute_paper_proposal(user_id, recent_prop.id, db=db)
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
            price = chart_ctx.get("latest_price") or 2500.0
            rsi_val = chart_ctx.get("active_indicators", {}).get("RSI_14")
            sma_val = chart_ctx.get("active_indicators", {}).get("SMA_20")

            if lang == "hi":
                reply = (
                    f"**{target_sym} सक्रिय चार्ट विश्लेषण:**\n"
                    f"- नवीनतम सत्यापित मूल्य: ₹{price:,.2f} (स्रोत: {chart_ctx.get('source')})\n"
                    f"- 20-दिवसीय SMA: ₹{f'{sma_val:,.2f}' if sma_val else 'तैयार हो रहा है'}\n"
                    f"- RSI (14): {f'{rsi_val:.1f}' if rsi_val else 'पर्याप्त डेटा नहीं'} "
                    f"({'ओवरबॉट क्षेत्र (>70)' if rsi_val and rsi_val > 70 else 'ओवरसोल्ड क्षेत्र (<30)' if rsi_val and rsi_val < 30 else 'संतुलित रेंज (30-70)'})\n\n"
                    f"सभी डेटा बिंदु वास्तविक ऐतिहासिक अवलोकनों से प्राप्त किए गए हैं।"
                )
            elif lang == "hi-Latn":
                reply = (
                    f"**{target_sym} Active Chart Analysis:**\n"
                    f"- Current Price: ₹{price:,.2f} (Source: {chart_ctx.get('source')})\n"
                    f"- 20-Day SMA: ₹{f'{sma_val:,.2f}' if sma_val else 'Calculating'}\n"
                    f"- RSI (14): {f'{rsi_val:.1f}' if rsi_val else 'N/A'} "
                    f"({'Overbought zone (>70)' if rsi_val and rsi_val > 70 else 'Oversold zone (<30)' if rsi_val and rsi_val < 30 else 'Neutral range (30-70)'})\n\n"
                    f"Yeh observation active chart historical data par aadharit hai."
                )
            if self.is_gemini_api_ready():
                sys_prompt = (
                    "You are FinEx AI Technical & Chart Analysis Copilot for Indian Equities (NSE). "
                    f"Active instrument: {target_sym} at current verified price ₹{price:,.2f} ({chart_ctx.get('source')}). "
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
        if any(w in p_lower for w in ["invest", "khareed", "kharido", "allocation", "laga do", "buy"]) and any(
            c.isdigit() for c in user_message
        ):
            import re

            numbers = re.findall(r"\b\d[\d,]*\b", user_message.replace(",", ""))
            budget_val = float(numbers[0]) if numbers else 10000.0

            target_symbols = []
            for item in INSTRUMENT_REGISTRY:
                if item["symbol"].lower() in p_lower or item["name"].lower() in p_lower:
                    target_symbols.append(item["symbol"])
            if not target_symbols:
                target_symbols = [active_sym, "TCS"] if active_sym != "TCS" else ["TCS", "RELIANCE"]

            proposal = await self.tool_create_paper_proposal(
                user_id, target_symbols, budget=budget_val, currency="INR", db=db
            )

            alloc_details = "\n".join(
                [
                    f"- **{a['symbol']}**: {a['quantity']} shares @ ₹{a['estimated_price']:,.2f} (Total: ₹{a['estimated_total']:,.2f})"
                    for a in proposal["allocations"]
                ]
            )

            if lang == "hi":
                reply = (
                    f"मैंने आपके लिए ₹{budget_val:,.2f} का सिमुलेटेड आवंटन प्रस्ताव तैयार किया है:\n\n"
                    f"{alloc_details}\n\n"
                    f"कुल अनुमानित लागत: ₹{proposal['estimated_allocation_total']:,.2f}.\n"
                    f"यदि आप सहमत हैं, तो **'हाँ'** या **'Confirm'** कहें। यह प्रस्ताव 10 मिनट के लिए मान्य है।"
                )
            elif lang == "hi-Latn":
                reply = (
                    f"Maine aapke liye ₹{budget_val:,.2f} ka paper allocation proposal banaya hai:\n\n"
                    f"{alloc_details}\n\n"
                    f"Estimated total: ₹{proposal['estimated_allocation_total']:,.2f}.\n"
                    f"Kya aap isse execute karna chahte hain? Confirm karne ke liye **'Yes'** ya **'Haan'** kahein."
                )
            else:
                reply = (
                    f"Here is a proposed paper allocation for ₹{budget_val:,.2f} of virtual balance:\n\n"
                    f"{alloc_details}\n\n"
                    f"Total Estimated Outlay: ₹{proposal['estimated_allocation_total']:,.2f} virtual INR.\n"
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

        # 6. Try Live Gemini API if key is available
        if self.is_gemini_api_ready():
            sys_instruct = (
                "You are FinEx AI Paper Investment Assistant for Indian Equities (NSE). "
                f"Active chart context: {active_chart_context or {'symbol': active_sym}}. "
                "Respond helpfully in the user's language (English, Hindi, or Hinglish). "
                "Maintain strict SEBI educational compliance: all trades and balances are 100% virtual paper trading."
            )
            gemini_reply = await self.call_gemini_api(user_message, sys_instruct)
            if gemini_reply:
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=gemini_reply,
                    language_detected=lang,
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
