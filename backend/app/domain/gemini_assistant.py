"""FinEx AI Paper Investment Assistant with Groq LPU Integration.

Tasks:
- Section 2: Conversational AI in English, Hindi, and Hinglish.
- Section 5: Typed tool schemas, server-owned user context, separate proposal & execution flows.
- Section 8I: get_chart_context tool for active chart understanding.
- Section 9: Server-side GROQ_API_KEY setup with graceful unconfigured degradation.

Strict Invariants:
1. Paper Trading Only: All trades, proposals, and balances are 100% virtual.
2. Derives user_id and account strictly from trusted server context.
3. Informational queries never create orders or proposals.
4. Proposals expire and require explicit authorization.
5. Never prints, logs, or transmits API keys.
"""

import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

import httpx
from backend.app.adapters.market_data_provider import INSTRUMENT_REGISTRY, RealMarketDataProvider
from backend.app.config import get_settings
from backend.app.domain.paper_trading_service import (
    OrderSubmitRequest,
    PaperTradingEngine,
)
from backend.app.domain.portfolio_intent_router import PortfolioIntent, PortfolioIntentRouter
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


_DIGIT_TRANS = str.maketrans("०१२३४५६७८९", "0123456789")

_HINGLISH_MARKERS = frozenset(
    {
        "kya",
        "kaise",
        "mera",
        "meri",
        "mere",
        "karo",
        "batao",
        "kharid",
        "khareed",
        "kharidna",
        "khareedna",
        "bech",
        "kitna",
        "kitne",
        "chahiye",
        "hai",
        "hain",
        "nahi",
        "kaunse",
        "kaha",
        "hoga",
        "muze",
        "mujhe",
        "yek",
        "ek",
        "lena",
        "lelo",
        "dikhao",
        "samjhao",
        "tum",
    }
)

_WORD_NUMBER_MAP: Dict[str, int] = {
    "ek": 1,
    "yek": 1,
    "ik": 1,
    "aik": 1,
    "one": 1,
    "single": 1,
    "एक": 1,
    "two": 2,
    "दो": 2,
    "teen": 3,
    "three": 3,
    "तीन": 3,
    "char": 4,
    "chaar": 4,
    "four": 4,
    "चार": 4,
    "panch": 5,
    "paanch": 5,
    "five": 5,
    "पांच": 5,
    "पाँच": 5,
    "chhah": 6,
    "chhe": 6,
    "six": 6,
    "छह": 6,
    "saat": 7,
    "seven": 7,
    "सात": 7,
    "aath": 8,
    "eight": 8,
    "आठ": 8,
    "nau": 9,
    "nine": 9,
    "नौ": 9,
    "das": 10,
    "ten": 10,
    "दस": 10,
}

_SYMBOL_ALIASES: Dict[str, str] = {
    "रिलायंस इंडस्ट्रीज": "RELIANCE",
    "रिलायंस": "RELIANCE",
    "tata consultancy": "TCS",
    "टीसीएस": "TCS",
    "infosys": "INFY",
    "इन्फोसिस": "INFY",
    "इंफोसिस": "INFY",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "एचडीएफसी": "HDFCBANK",
    "icici bank": "ICICIBANK",
    "icici": "ICICIBANK",
    "आईसीआईसीआई": "ICICIBANK",
    "state bank": "SBIN",
    "sbi": "SBIN",
    "एसबीआई": "SBIN",
    "wipro": "WIPRO",
    "विप्रो": "WIPRO",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "भारती एयरटेल": "BHARTIARTL",
    "tata motors": "TATAMOTORS",
    "टाटा मोटर्स": "TATAMOTORS",
    "tata steel": "TATASTEEL",
    "टाटा स्टील": "TATASTEEL",
    "kotak": "KOTAKBANK",
    "कोटक": "KOTAKBANK",
    "bajaj finance": "BAJFINANCE",
    "बजाज फाइनेंस": "BAJFINANCE",
    "maruti": "MARUTI",
    "मारुति": "MARUTI",
    "sun pharma": "SUNPHARMA",
    "सन फार्मा": "SUNPHARMA",
    "zomato": "ZOMATO",
    "जोमैटो": "ZOMATO",
    "reliance": "RELIANCE",
    "asian paints": "ASIANPAINT",
    "axis bank": "AXISBANK",
    "tech mahindra": "TECHM",
    "hcl tech": "HCLTECH",
    "larsen": "LT",
    "bharat electronics": "BEL",
    "hindustan aeronautics": "HAL",
}

_UPPER_TICKER_STOPWORDS = frozenset(
    {
        "NSE",
        "BSE",
        "INR",
        "USD",
        "RS",
        "AI",
        "BUY",
        "SELL",
        "SHARE",
        "SHARES",
        "STOCK",
        "STOCKS",
        "QTY",
        "PORTFOLIO",
        "RSI",
        "SMA",
        "EMA",
        "MACD",
        "VWAP",
        "YES",
        "NO",
        "OK",
        "HI",
        "HEY",
        "MY",
        "ME",
        "FOR",
        "IN",
        "OF",
        "TO",
        "AND",
        "OR",
        "THE",
        "A",
        "AN",
        "I",
    }
)


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
    def __init__(
        self,
        engine: Optional[PaperTradingEngine] = None,
        provider: Optional[RealMarketDataProvider] = None,
        settings: Optional[Any] = None,
    ):
        self._provider = provider
        self._engine = engine
        self._settings = settings
        self._verified_working = False
        self._last_verified_at: Optional[float] = None
        self._last_verification_attempt: Optional[float] = None

    @property
    def settings(self):
        if self._settings is not None:
            return self._settings
        return get_settings()

    @settings.setter
    def settings(self, val):
        self._settings = val

    @property
    def provider(self) -> RealMarketDataProvider:
        if self._provider is not None:
            return self._provider
        return RealMarketDataProvider(
            force_cache=False, allow_fixture_fallback=getattr(self.settings, "MARKET_ALLOW_FIXTURES", False)
        )

    @property
    def engine(self) -> PaperTradingEngine:
        if self._engine is not None:
            return self._engine
        return PaperTradingEngine(market_provider=self.provider)

    def is_groq_api_ready(self) -> bool:
        """Verify if a valid GROQ_API_KEY is configured."""
        key = getattr(self.settings, "GROQ_API_KEY", None)
        if not key or "YOUR_GROQ_API_KEY" in key or "placeholder" in key.lower():
            return False
        return len(key.strip()) >= 10

    def is_gemini_api_ready(self) -> bool:
        """Deprecated: Gemini provider removed. Returns False."""
        return False

    def is_llm_ready(self) -> bool:
        """Verify if the supported LLM provider (Groq) is ready."""
        if getattr(self.settings, "LLM_PROVIDER", "").lower() in ("mock", "offline", "simulated", "local"):
            return False
        return self.is_groq_api_ready()

    def is_configured(self) -> bool:
        """Verify if assistant is configured with a valid API key format and active provider."""
        return self.is_llm_ready()

    def is_verified_working(self) -> bool:
        """Verify if live LLM connection has been verified working."""
        return bool(self._verified_working and self.is_llm_ready())

    def get_provider_info(self) -> Dict[str, str]:
        """Return active provider identification and model for status reporting."""
        if not self.is_llm_ready():
            return {
                "provider": "mock-offline",
                "model": "deterministic-engine",
            }
        return {
            "provider": "groq-live" if self.is_verified_working() else "groq-configured",
            "model": getattr(self.settings, "GROQ_MODEL", "openai/gpt-oss-120b"),
        }

    async def verify_live_connection(self, force: bool = False) -> bool:
        """Test and verify connectivity by pinging active LLM API if not already verified."""
        if not self.is_llm_ready():
            self._verified_working = False
            return False
        if self._verified_working and not force:
            return True

        # Throttle repeated failed verification attempts to avoid hammering upstream LLM quotas (cooldown: 120s)
        now = time.monotonic()
        if not force and self._last_verification_attempt is not None:
            if (now - self._last_verification_attempt) < 120.0:
                return self.is_verified_working()

        self._last_verification_attempt = now
        res = await self.call_llm_api("ping", "Respond strictly with pong")
        if res and res.strip():
            self._verified_working = True
            self._last_verified_at = now
            return True

        self._verified_working = False
        return False

    async def call_groq_api(self, prompt: str, system_instruction: str) -> Optional[str]:
        """Invoke Groq Cloud API using OpenAI-compatible chat completions with prompt fallback."""
        if not self.is_llm_ready():
            self._verified_working = False
            return None

        groq_key = getattr(self.settings, "GROQ_API_KEY", "") or ""
        if not groq_key or len(groq_key.strip()) < 10:
            self._verified_working = False
            return None

        pref_model = getattr(self.settings, "GROQ_MODEL", "openai/gpt-oss-120b") or "openai/gpt-oss-120b"
        total_timeout = float(getattr(self.settings, "GROQ_TIMEOUT", 8.0) or 8.0)
        per_attempt_timeout = min(5.0, total_timeout)

        # Primary configured model + fallback candidate for model-specific errors (404/400/429/503)
        candidate_models = [
            pref_model,
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
        ]
        models_to_try = list(dict.fromkeys(candidate_models))[:2]

        headers = {
            "Authorization": f"Bearer {groq_key.strip()}",
            "Content-Type": "application/json",
        }
        url = "https://api.groq.com/openai/v1/chat/completions"
        start_time = time.monotonic()

        for _idx, model in enumerate(models_to_try):
            elapsed = time.monotonic() - start_time
            remaining = total_timeout - elapsed
            if remaining <= 1.0:
                print(
                    f"[GroqAssistant] Total timeout budget ({total_timeout}s) exhausted. Falling back to local engine."
                )
                break

            current_timeout = min(per_attempt_timeout, remaining)
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 2048,
            }

            try:
                limits = httpx.Timeout(current_timeout, connect=min(2.5, current_timeout))
                async with httpx.AsyncClient(timeout=limits) as client:
                    res = await client.post(url, json=payload, headers=headers)

                    if res.status_code == 200:
                        try:
                            data = res.json()
                            choices = data.get("choices", [])
                            if choices:
                                content = choices[0].get("message", {}).get("content", "")
                                if content and isinstance(content, str) and content.strip():
                                    self._verified_working = True
                                    return content.strip()
                                print(f"[GroqAssistant] Model {model} returned HTTP 200 with empty content.")
                            else:
                                print(f"[GroqAssistant] Model {model} returned HTTP 200 with empty choices array.")
                        except Exception as parse_err:
                            print(f"[GroqAssistant] JSON parse error on HTTP 200 from {model}: {parse_err}")
                        # HTTP 200 without usable content does not verify live connection and aborts
                        break

                    elif res.status_code in (401, 403):
                        print(f"[GroqAssistant] Auth error ({res.status_code}): Invalid or unauthorized credentials.")
                        # Authentication error is fatal across all models
                        break

                    elif res.status_code in (400, 404, 422, 429, 503):
                        # Model-specific or capacity issue; allow fallback to next candidate if time permits
                        print(
                            f"[GroqAssistant] Model {model} returned status {res.status_code}. Attempting fallback if available."
                        )
                        continue

                    else:
                        print(f"[GroqAssistant] Unexpected HTTP status {res.status_code} from {model}.")
                        break

            except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
                print(
                    f"[GroqAssistant] Host connection failed ({type(conn_err).__name__}). Aborting further model attempts."
                )
                break
            except httpx.TimeoutException as to_err:
                print(
                    f"[GroqAssistant] Request timed out on model {model} ({type(to_err).__name__}). Aborting to preserve response latency."
                )
                break
            except Exception as e:
                print(f"[GroqAssistant] Unexpected error for model {model}: {type(e).__name__} - {e}")
                break

        # Succeeded call returns early; reaching here indicates API failed or timed out
        self._verified_working = False
        return None

    async def call_llm_api(self, prompt: str, system_instruction: str) -> Optional[str]:
        """Direct call to active Groq LLM API with graceful degradation to None."""
        return await self.call_groq_api(prompt, system_instruction)

    def detect_language(self, prompt: str) -> str:
        """Detect language: English ('en'), Hindi ('hi'), or Hinglish ('hi-Latn')."""
        p_lower = prompt.lower()
        # Hindi Devanagari script detection
        if any("\u0900" <= char <= "\u097f" for char in prompt):
            return "hi"
        tokens = set(re.findall(r"[a-z]+", p_lower))
        if tokens & _HINGLISH_MARKERS or any(p in p_lower for p in ("le do", "le lo", "laga do", "kar do")):
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
            return await self.engine.get_portfolio_summary_db(user_id, db=db)
        return self.engine.get_portfolio_summary(user_id)

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
        budget: Optional[float] = None,
        currency: str = "INR",
        rationale: str = "Assistant recommended allocation",
        conversation_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        requested_quantities: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Create a server-validated bounded paper buy/allocation proposal with expiration."""
        import math

        if not symbols:
            return {
                "status": "REJECTED",
                "error": "At least one symbol required for a paper trade proposal.",
                "allocations": [],
                "total_budget": float(budget) if budget is not None and math.isfinite(budget) else 0.0,
                "requested_budget": float(budget) if budget is not None and math.isfinite(budget) else 0.0,
                "requires_approval": False,
                "disclaimer": SIMULATION_DISCLAIMER,
            }

        # Fetch caller's authoritative virtual cash balance up front
        if db:
            acct = await self.engine.get_or_create_account_db(user_id, db=db)
            available_cash = Decimal(str(acct.current_cash))
            account_id = acct.id
        else:
            acct = self.engine.get_or_create_account(user_id)
            available_cash = Decimal(str(acct["current_cash"]))
            account_id = acct["id"]

        allocations: List[Dict[str, Any]] = []
        total_estimated = Decimal("0.00")
        unaffordable_symbols = []
        unavailable_symbols = []

        if requested_quantities:
            for sym in symbols:
                clean_sym = sym.upper().strip()
                qty = int(requested_quantities.get(clean_sym, 0))
                if qty <= 0:
                    return {
                        "status": "REJECTED",
                        "error": f"Share quantity for {clean_sym} must be a positive whole number.",
                        "allocations": [],
                        "total_budget": 0.0,
                        "requested_budget": 0.0,
                        "requires_approval": False,
                        "disclaimer": SIMULATION_DISCLAIMER,
                    }
                q = await self.provider.get_latest_quote(clean_sym)
                if not q or q.price <= Decimal("0.00") or q.is_stale or q.data_status == "stale":
                    unavailable_symbols.append(clean_sym)
                    continue
                price = Decimal(str(q.price))
                leg_total = (Decimal(qty) * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_estimated += leg_total
                allocations.append(
                    {
                        "symbol": clean_sym,
                        "side": "BUY",
                        "quantity": qty,
                        "estimated_price": round(float(price), 2),
                        "estimated_total": round(float(leg_total), 2),
                        "currency": currency,
                    }
                )

            if unavailable_symbols:
                return {
                    "status": "QUOTE_UNAVAILABLE",
                    "error": (
                        f"Verified market quote for {', '.join(unavailable_symbols)} is currently unavailable. "
                        "Cannot prepare a virtual order preview without a valid price."
                    ),
                    "unavailable_symbols": unavailable_symbols,
                    "allocations": [],
                    "total_budget": 0.0,
                    "requested_budget": 0.0,
                    "requires_approval": False,
                    "disclaimer": SIMULATION_DISCLAIMER,
                }

            if total_estimated > available_cash:
                return {
                    "status": "INSUFFICIENT_CASH",
                    "error": (
                        f"Estimated virtual outlay ₹{total_estimated:,.2f} exceeds your available virtual cash "
                        f"balance of ₹{available_cash:,.2f}."
                    ),
                    "requested_budget": round(float(total_estimated), 2),
                    "estimated_allocation_total": round(float(total_estimated), 2),
                    "available_cash": round(float(available_cash), 2),
                    "allocations": allocations,
                    "requires_approval": False,
                    "disclaimer": SIMULATION_DISCLAIMER,
                }

            budget_dec = total_estimated
            budget_val = round(float(total_estimated), 2)
            qty_desc = ", ".join(f"{a['quantity']}x {a['symbol']}" for a in allocations)
            instruction_text = f"Buy {qty_desc} (virtual)"
        else:
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

            # Treat requested budget as a hard maximum
            budget_dec = Decimal(str(budget))
            per_stock_budget = budget_dec / Decimal(len(symbols))

            for sym in symbols:
                clean_sym = sym.upper().strip()
                q = await self.provider.get_latest_quote(clean_sym)
                if not q or q.price <= Decimal("0.00") or q.is_stale or q.data_status == "stale":
                    unavailable_symbols.append(clean_sym)
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
                        "side": "BUY",
                        "quantity": qty,
                        "estimated_price": round(float(price), 2),
                        "estimated_total": round(float(leg_total), 2),
                        "currency": currency,
                    }
                )

            if not allocations:
                if unavailable_symbols and not unaffordable_symbols:
                    return {
                        "status": "QUOTE_UNAVAILABLE",
                        "error": (
                            f"Verified market quote unavailable for {', '.join(unavailable_symbols)}. "
                            "Cannot prepare a virtual order preview without a valid price."
                        ),
                        "unavailable_symbols": unavailable_symbols,
                        "requested_budget": float(budget),
                        "estimated_allocation_total": 0.0,
                        "allocations": [],
                        "requires_approval": False,
                        "disclaimer": SIMULATION_DISCLAIMER,
                    }
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

            budget_val = round(float(budget), 2)
            instruction_text = f"Invest {currency} {budget_val:,.2f} across {', '.join(symbols)}"

        proposal_id = f"prop-{uuid.uuid4().hex[:12]}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        if db:
            prop = PaperProposal(
                id=proposal_id,
                user_id=user_id,
                account_id=account_id,
                conversation_id=conversation_id,
                instruction_text=instruction_text,
                proposed_allocations=allocations,
                requested_budget=Decimal(str(round(budget_val, 2))),
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
            "symbols": [a["symbol"] for a in allocations],
            "requested_budget": budget_val,
            "total_budget": round(float(total_estimated), 2),
            "estimated_allocation_total": round(float(total_estimated), 2),
            "available_cash": round(float(available_cash), 2),
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
        """Provide detailed chart context for active chart understanding."""
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

    _SAFE_SYMBOL_RE = re.compile(r"^[A-Z0-9 ._-]{1,25}$")
    _ALLOWED_INTERVALS = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W", "1M"})
    _intent_router = PortfolioIntentRouter()

    @classmethod
    def _sanitize_chart_context(cls, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Allow only strictly typed chart context fields to prevent prompt injection."""
        if not ctx or not isinstance(ctx, dict):
            return {"symbol": "RELIANCE"}
        raw_sym = str(ctx.get("symbol", "RELIANCE")).upper().strip()
        safe_sym = raw_sym if cls._SAFE_SYMBOL_RE.fullmatch(raw_sym) else "RELIANCE"
        sanitized: Dict[str, Any] = {"symbol": safe_sym}
        raw_tf = ctx.get("timeframe") or ctx.get("interval")
        if isinstance(raw_tf, str) and raw_tf.strip() in cls._ALLOWED_INTERVALS:
            sanitized["timeframe"] = raw_tf.strip()
        return sanitized

    @staticmethod
    def _extract_symbols(user_message: str) -> tuple[List[str], List[str]]:
        """Extract supported NSE symbols and unrecognized uppercase ticker candidates."""
        p_lower = user_message.lower()
        found: List[str] = []

        def _add_sym(sym: str) -> None:
            if sym not in found:
                found.append(sym)

        # Check explicit Hindi/English company aliases (longest keys first)
        for alias in sorted(_SYMBOL_ALIASES.keys(), key=len, reverse=True):
            if any("\u0900" <= c <= "\u097f" for c in alias):
                if alias in user_message:
                    _add_sym(_SYMBOL_ALIASES[alias])
            elif re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", p_lower):
                _add_sym(_SYMBOL_ALIASES[alias])

        # Check canonical symbols and full registered names with token boundaries
        for item in INSTRUMENT_REGISTRY:
            sym = item["symbol"]
            if re.search(rf"(?<![a-z0-9]){re.escape(sym.lower())}(?![a-z0-9])", p_lower):
                _add_sym(sym)
                continue
            full_name = item["name"].lower()
            if re.search(rf"(?<![a-z0-9]){re.escape(full_name)}(?![a-z0-9])", p_lower):
                _add_sym(sym)

        known_upper = {item["symbol"].upper() for item in INSTRUMENT_REGISTRY}
        unknown_upper = [
            tok
            for tok in re.findall(r"\b[A-Z]{2,12}\b", user_message)
            if tok not in known_upper and tok not in _UPPER_TICKER_STOPWORDS
        ]
        return found, list(dict.fromkeys(unknown_upper))

    @staticmethod
    def _has_buy_action_intent(p_lower: str, raw_message: str) -> bool:
        """Detect clear English, Hindi, or Hinglish actionable buy/invest requests."""
        negated = (
            "do not buy",
            "don't buy",
            "dont buy",
            "do not invest",
            "don't invest",
            "dont invest",
            "mat kharid",
            "mat lena",
            "nahi kharidna",
            "nahi lena",
            "not buy",
        )
        if any(n in p_lower for n in negated):
            return False

        ascii_patterns = (
            r"\bbuy\b",
            r"\bpurchase\b",
            r"\binvest\b",
            r"\ballocate\b",
            r"\ballocation\b",
            r"\bkhar(?:ee|i)d(?:na|ne|o)?\b",
            r"\blen[ae]\s+h(?:ai|ain|)\b",
            r"\ble\s*(?:lo|do(?:\s*ge)?|dijiye|le)\b",
            r"\blelo\b",
            r"\blaga\s*do\b",
            r"\blagana\s+h(?:ai|ain)\b",
            r"\badd\s+.+\s+(?:to|in)\s+(?:my\s+)?portfolio\b",
            r"\bmere\s+portfolio\s+m(?:ee|e|ein)\s+.+\b(?:le|add|dal|daal)\b",
        )
        if any(re.search(pat, p_lower) for pat in ascii_patterns):
            return True

        hindi_tokens = ("खरीद", "लेना", "लेने", "ले दो", "ले लो", "लीजिए", "इन्वेस्ट", "निवेश", "लगा दो")
        return any(tok in raw_message for tok in hindi_tokens)

    @staticmethod
    def _has_sell_intent(p_lower: str, raw_message: str) -> bool:
        return bool(re.search(r"\bsell\b|\bbech(?:na|ne|o| do| de)?\b", p_lower) or "बेच" in raw_message)

    @staticmethod
    def _is_advisory_research_query(p_lower: str, raw_message: str) -> bool:
        """Detect pure educational/advisory questions ('Should I buy?', 'Is it good?')."""
        advisory_prefixes = (
            "should i",
            "is it good",
            "is it a good",
            "is it safe",
            "why ",
            "what ",
            "how ",
            "which ",
            "tell me about",
            "explain",
            "analysis of",
            "review",
            "kya mujhe",
            "kya yeh",
            "kya ye",
            "kaun sa",
            "kaunsa",
        )
        advisory_phrases = (
            "should i invest",
            "should i buy",
            "is it good to invest",
            "is it good to buy",
            "is it safe to invest",
            "worth buying",
            "good time to buy",
            "kya invest karna chahiye",
            "kya buy karna chahiye",
            "kharidna chahiye",
            "khareedna chahiye",
            "lena chahiye",
            "lene chahiye",
            "chahiye kya",
            "would you recommend",
            "would you suggest",
            "kya lagta hai",
        )
        hindi_advisory = ("चाहिए", "कैसा है", "क्या मुझे खरीदना")
        return (
            p_lower.startswith(advisory_prefixes)
            or any(phrase in p_lower for phrase in advisory_phrases)
            or any(h in raw_message for h in hindi_advisory)
        )

    @staticmethod
    def _extract_quantity_or_budget(user_message: str, p_lower: str) -> Dict[str, Any]:
        """Parse whole share quantity or INR budget from English, Hindi, and Hinglish text."""
        norm_text = user_message.translate(_DIGIT_TRANS)
        norm_lower = norm_text.lower()

        has_currency_hint = bool(
            "₹" in norm_text
            or re.search(
                r"\b(?:inr|rs\.?|rupees?|rupaya|rupaye|budget|worth|laga\s*do|lagao|allocate|allocation)\b", norm_lower
            )
            or (
                re.search(r"\binvest\b|इन्वेस्ट|निवेश", norm_lower)
                and not re.search(r"\b(?:share|shares|stock|stocks|qty|quantity|unit|units)\b|शेयर", norm_lower)
            )
        )

        # Reject explicit negative or zero amounts instead of executing wrong defaults
        neg_or_zero = re.search(
            r"(?:^|\s)(-\d+(?:\.\d+)?|0(?:\.0+)?)\s*(?:share|shares|stock|stocks|rs|inr)?\b", norm_lower
        )
        if neg_or_zero and not has_currency_hint:
            return {"mode": "invalid_qty"}

        # Detect fractional shares when share unit is requested
        frac_share = re.search(
            r"\b\d+\.\d+\s*(?:[a-z0-9&.-]+\s+)?(?:share|shares|stock|stocks|unit|units)\b", norm_lower
        )
        if frac_share:
            return {"mode": "invalid_qty"}

        # Extract plain numeric values (ignoring commas in amounts like 10,000)
        num_matches = re.findall(r"(?<![a-zA-Z-])\d+(?:,\d{3})*(?:\.\d+)?(?![a-zA-Z-])", norm_text)
        parsed_nums = [float(n.replace(",", "")) for n in num_matches]

        if parsed_nums:
            val = parsed_nums[0]
            if val <= 0:
                return {"mode": "invalid_qty"}
            if has_currency_hint:
                return {"mode": "budget", "budget": val}
            if float(val).is_integer():
                return {"mode": "quantity", "quantity": int(val)}
            return {"mode": "invalid_qty"}

        # Check English/Hindi/Hinglish word numbers ("yek", "ek", "एक", "one", etc.)
        for word, num_val in _WORD_NUMBER_MAP.items():
            if any("\u0900" <= c <= "\u097f" for c in word):
                if word in norm_text:
                    return {"mode": "quantity", "quantity": num_val}
            elif re.search(rf"\b{re.escape(word)}\b", norm_lower):
                return {"mode": "quantity", "quantity": num_val}

        # Handle Hinglish "do" = 2 only when modifying shares/stocks (never "le do", "laga do", "kar do")
        if re.search(
            r"(?<!\ble\s)(?<!\bkar\s)(?<!\bde\s)(?<!\bbata\s)(?<!\blaga\s)\bdo\s+(?:[a-z0-9&.-]+\s+){0,2}(?:shares?|stocks?|qty|quantity|units?|ke|ka|kaa)\b",
            norm_lower,
        ):
            return {"mode": "quantity", "quantity": 2}

        # Handle English article phrasing ("buy a share", "buy a RELIANCE share")
        if re.search(r"\b(?:a|an)\s+(?:[a-z0-9&.-]+\s+){0,2}shares?\b", norm_lower):
            return {"mode": "quantity", "quantity": 1}

        return {"mode": "missing"}

    @staticmethod
    def _format_portfolio_summary_reply(summary: Dict[str, Any], lang: str, active_sym: str) -> str:
        """Render authoritative virtual portfolio summary without silent zero or cash fallbacks."""
        raw_cash = summary.get("current_cash")
        if raw_cash is None:
            raw_cash = summary.get("cash_balance")

        raw_equity = summary.get("total_equity")
        if raw_equity is None:
            raw_equity = summary.get("total_portfolio_value")
        if raw_equity is None:
            raw_equity = summary.get("equity")

        cash_str = f"₹{float(raw_cash):,.2f}" if raw_cash is not None else "Unavailable"
        equity_str = f"₹{float(raw_equity):,.2f}" if raw_equity is not None else "Unavailable"

        positions = summary.get("positions")
        if positions is None:
            pos_text = "- Holdings data unavailable."
            pos_count_label = "Unavailable"
        elif positions:
            pos_lines = []
            for p in positions:
                sym = p.get("symbol") or "UNKNOWN"
                raw_qty = p.get("quantity")
                qty_str = (
                    f"{raw_qty:g}"
                    if isinstance(raw_qty, (int, float))
                    else (str(raw_qty) if raw_qty is not None else "Unavailable")
                )

                raw_avg = p.get("average_buy_price")
                if raw_avg is None:
                    raw_avg = p.get("avg_cost")
                if raw_avg is None:
                    raw_avg = p.get("avg_entry_price")
                avg_str = f"₹{float(raw_avg):,.2f}" if raw_avg is not None else "Unavailable"

                raw_mkt_val = p.get("market_value")
                mkt_str = f" | Value: ₹{float(raw_mkt_val):,.2f}" if raw_mkt_val is not None else ""
                pos_lines.append(f"- **{sym}**: {qty_str} shares @ avg {avg_str}{mkt_str}")
            pos_text = "\n".join(pos_lines)
            pos_count_label = str(len(positions))
        else:
            pos_text = "- No open positions in your virtual ledger yet."
            pos_count_label = "0"

        if lang == "hi":
            return (
                f"**आपका वर्चुअल पेपर पोर्टफोलियो:**\n\n"
                f"- उपलब्ध वर्चुअल कैश: {cash_str}\n"
                f"- कुल पोर्टफोलियो इक्विटी: {equity_str}\n\n"
                f"**सक्रिय पोजीशन्स ({pos_count_label}):**\n"
                f"{pos_text}\n\n"
                f"नया पेपर ऑर्डर प्रिव्यू बनाने के लिए शेयर और मात्रा बताएं (उदा: 'Buy 1 {active_sym} share' या '₹10,000 इन्वेस्ट करो')।"
            )
        if lang == "hi-Latn":
            return (
                f"**Aapka Virtual Paper Portfolio:**\n\n"
                f"- Available Virtual Cash: {cash_str}\n"
                f"- Total Portfolio Equity: {equity_str}\n\n"
                f"**Active Positions ({pos_count_label}):**\n"
                f"{pos_text}\n\n"
                f"Virtual buy preview ke liye stock aur quantity ya budget batayein (jaise: 'Buy 1 {active_sym} share' ya 'Invest 10000 in {active_sym}')."
            )
        return (
            f"**Your Virtual Paper Portfolio Summary:**\n\n"
            f"- Available Virtual Cash: {cash_str}\n"
            f"- Total Portfolio Equity: {equity_str}\n\n"
            f"**Active Positions ({pos_count_label}):**\n"
            f"{pos_text}\n\n"
            f"To preview a virtual trade, say e.g. *'Buy 1 share of {active_sym}'* or *'Invest INR 25,000 across Nifty leaders'*."
        )

    @staticmethod
    def _format_proposal_preview_reply(proposal: Dict[str, Any], lang: str, is_quantity_order: bool) -> str:
        """Render a bounded virtual paper order preview requiring explicit confirmation."""
        alloc_details = "\n".join(
            [
                f"- **{a.get('side', 'BUY')} {a['quantity']}x {a['symbol']}** @ ₹{a['estimated_price']:,.2f} (Est. Total: ₹{a['estimated_total']:,.2f})"
                for a in proposal.get("allocations", [])
            ]
        )
        est_total = proposal.get("estimated_allocation_total")
        est_str = f"₹{float(est_total):,.2f}" if est_total is not None else "Unavailable"
        avail_cash = proposal.get("available_cash")
        cash_note = f"Available virtual cash: ₹{float(avail_cash):,.2f}.\n" if avail_cash is not None else ""

        if lang == "hi":
            header = "मैंने आपका **वर्चुअल पेपर BUY ऑर्डर प्रिव्यू** तैयार किया है (अभी कोई ऑर्डर निष्पादित नहीं हुआ है):"
            return (
                f"{header}\n\n{alloc_details}\n\n"
                f"कुल अनुमानित वर्चुअल लागत: {est_str}\n{cash_note}"
                f"पुष्टि करने के लिए **'हाँ'** / **'Confirm'** लिखें या **Execute Paper Proposal** बटन दबाएं। (10 मिनट में समाप्त होगा)"
            )
        if lang == "hi-Latn":
            header = (
                "Maine aapke liye **Virtual Paper BUY Order Preview** taiyar kiya hai (abhi koi order place nahi hua hai):"
                if is_quantity_order
                else "Maine aapke liye virtual paper allocation preview taiyar kiya hai (abhi koi order place nahi hua hai):"
            )
            return (
                f"{header}\n\n{alloc_details}\n\n"
                f"Total estimated virtual cost: {est_str}\n{cash_note}"
                f"Kya aap yeh virtual order place karna chahte hain? Confirm karne ke liye **'Yes'** / **'Haan'** / **'Confirm'** likhein ya **Execute Paper Proposal** click karein (10 min valid)."
            )
        header = (
            "Here is your **Virtual Paper BUY Order Preview** (no order has been placed yet):"
            if is_quantity_order
            else "Here is a proposed virtual paper allocation preview (no order has been placed yet):"
        )
        return (
            f"{header}\n\n{alloc_details}\n\n"
            f"Total Estimated Outlay: {est_str} virtual INR\n{cash_note}"
            f"To confirm and execute this virtual order, reply **'Yes'** / **'Confirm'** or click **Execute Paper Proposal** (expires in 10 minutes)."
        )

    @staticmethod
    def _build_clarification_reply(reason: str, lang: str, symbols: List[str], active_sym: str, extra: str = "") -> str:
        """Build a concise, localized clarification without executing or creating a proposal."""
        sym_label = ", ".join(symbols) if symbols else active_sym
        if reason == "missing_symbol":
            if lang == "hi":
                return f"कृपया बताएं कि आप कौन-सा शेयर वर्चुअल रूप से खरीदना चाहते हैं (उदा: **{active_sym}** या **TCS**) और कितनी मात्रा में?"
            if lang == "hi-Latn":
                return f"Kripya stock symbol confirm karein ki aap kaunsa share virtual portfolio me lena chahte hain (jaise **{active_sym}** ya **TCS**)?"
            return f"Which stock symbol would you like to preview a virtual buy for (for example, **{active_sym}** or **TCS**)?"
        if reason == "missing_amount":
            if lang == "hi":
                return f"आप **{sym_label}** के कितने वर्चुअल शेयर खरीदना चाहते हैं (या कितना वर्चुअल बजट ₹ में लगाना चाहते हैं)?"
            if lang == "hi-Latn":
                return f"Aap **{sym_label}** ke kitne virtual shares lena chahte hain (ya kitna INR budget lagana chahte hain)?"
            return f"How many virtual shares of **{sym_label}** (or what INR budget) would you like me to preview?"
        if reason == "invalid_qty":
            if lang == "hi-Latn":
                return f"Kripya **{sym_label}** ke liye positive whole number share quantity batayein (jaise: 1, 2 ya 5 shares)."
            if lang == "hi":
                return f"कृपया **{sym_label}** के लिए एक सकारात्मक पूर्ण संख्या (जैसे 1, 2 या 5 शेयर) बताएं।"
            return f"Please specify a positive whole number of shares for **{sym_label}** (e.g., 1, 2, or 5 shares)."
        if reason == "ambiguous_symbols":
            if lang == "hi-Latn":
                return f"Aapne ek se zyada stocks ({sym_label}) mention kiye hain. Kripya batayein ki aapko kaunse ek stock ka share lena hai, ya sabhi ke liye INR budget dein."
            if lang == "hi":
                return f"आपने एक से अधिक स्टॉक्स ({sym_label}) लिखे हैं। कृपया स्पष्ट करें कि किस एक स्टॉक के कितने शेयर लेने हैं या कुल INR बजट बताएं।"
            return f"You mentioned multiple symbols ({sym_label}). Please clarify which single stock quantity you want to buy, or specify a total INR budget."
        if reason == "unknown_symbol":
            if lang == "hi-Latn":
                return f"**{extra}** FinEx ke supported virtual equity list me nahi mila. Kripya valid NSE symbol dein (jaise RELIANCE, TCS, INFY, HDFCBANK)."
            if lang == "hi":
                return f"**{extra}** FinEx की समर्थित वर्चुअल इक्विटी सूची में नहीं मिला। कृपया मान्य NSE प्रतीक दें (जैसे RELIANCE, TCS, INFY)।"
            return f"**{extra}** is not in FinEx's supported virtual equities list. Please specify a supported NSE symbol such as RELIANCE, TCS, or INFY."
        if reason == "sell_or_mixed":
            if lang == "hi-Latn":
                return "AskFinEx AI abhi sirf virtual **BUY** order preview banata hai. Sell ya mixed action ke liye please confirm karein ki aap virtual BUY chahte hain, ya Order Ticket use karein."
            return "AskFinEx AI currently prepares virtual **BUY** order previews only. Please clarify if you want a virtual BUY order, or use the Order Ticket for simulated sell orders."
        # ambiguous_intent
        if lang == "hi-Latn":
            return f"Kya aap **{sym_label}** ka virtual portfolio holding check karna chahte hain, ya **{sym_label}** buy karne ka virtual order preview banana hai? Kripya clear karein."
        if lang == "hi":
            return f"क्या आप **{sym_label}** की पोर्टफोलियो होल्डिंग देखना चाहते हैं या नया वर्चुअल BUY ऑर्डर प्रिव्यू बनाना चाहते हैं? कृपया स्पष्ट करें।"
        return f"Do you want to check your existing **{sym_label}** virtual holding, or prepare a virtual BUY order preview? Please clarify with your desired action and share quantity."

    async def process_user_turn(
        self,
        user_id: str,
        user_message: str,
        conversation_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        active_chart_context: Optional[Dict[str, Any]] = None,
    ) -> AssistantMessageResponse:
        """Process user message using Groq LPU with function calling and server-verified execution."""
        msg_id = f"msg-{uuid.uuid4().hex[:12]}"
        conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        lang = self.detect_language(user_message)
        p_lower = user_message.lower().strip()

        # 0. Guard against prompt injection and cross-user probing
        route_res = self._intent_router.route(user_message, caller_user_id=user_id)
        if route_res.predicted_intent == PortfolioIntent.UNAUTHORIZED_ACCESS:
            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=route_res.refusal_reason
                or "Access denied: FinEx AI strictly restricts access to your own account and immutable guidelines.",
                language_detected=lang,
                is_setup_incomplete=False,
            )

        # Resolve strictly sanitized active chart context
        safe_chart_context = self._sanitize_chart_context(active_chart_context)
        active_sym = safe_chart_context["symbol"]

        # 1. Intent pre-classification (Advisory research vs actionable buy/sell)
        is_advisory = self._is_advisory_research_query(p_lower, user_message)
        has_buy_intent = self._has_buy_action_intent(p_lower, user_message)
        has_sell_intent = self._has_sell_intent(p_lower, user_message)
        is_research_query = is_advisory or (
            user_message.strip().endswith("?") and not has_buy_intent and not has_sell_intent
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
            "cancel kar do",
            "abort trade",
            "stop execution",
            "mat karo",
            "mat lo",
            "nahi chahiye",
            "rehne do",
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
            "हाँ",
            "theek hai",
            "execute proposal",
            "confirm proposal",
            "yes execute",
            "yes proceed",
            "yes confirm",
            "yes buy",
            "confirm buy",
            "confirm order",
            "order confirm",
            "confirm kar do",
            "haan execute",
            "haan le lo",
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
            raw_cash_after = exec_result.get("cash_balance_after")
            cash_after_str = f"₹{float(raw_cash_after):,.2f}" if raw_cash_after is not None else "Unavailable"

            if status == "EXECUTED":
                if lang in ("hi", "hi-Latn"):
                    reply = (
                        f"Aapka paper order safalta-purvak execute ho gaya hai! Virtual cash balance: {cash_after_str}."
                    )
                else:
                    reply = f"Paper allocation executed successfully! Remaining virtual cash balance: {cash_after_str}."
            elif status == "PARTIALLY_EXECUTED":
                reply = (
                    f"Paper allocation partially executed. Some order legs filled, but others could not be completed. "
                    f"Check receipts for details. Remaining virtual cash: {cash_after_str}."
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
        if (
            is_greeting
            and not has_buy_intent
            and not has_sell_intent
            and not any(w in p_lower for w in ["invest", "buy", "chart", "rsi", "balance", "portfolio"])
        ):
            if self.is_llm_ready():
                sys_instruct = (
                    "You are FinEx AI Paper Investment Assistant for Indian Equities (NSE). "
                    f"Active chart instrument: {active_sym}. "
                    f"Respond warmly and helpfully in '{lang}' (English, Hindi, or Hinglish as appropriate). "
                    f"Greet the user, note you are powered by FinEx AI, and suggest 3 quick ideas they can explore: "
                    f"1) Technical analysis on {active_sym} chart & indicators (RSI, SMA), "
                    f"2) Propose paper portfolio trades (e.g. 'Invest ₹15,000 in {active_sym} and TCS'), "
                    f"3) Check their virtual paper trading balance. Keep your answer concise and welcoming."
                )
                llm_text = await self.call_llm_api(user_message, sys_instruct)
                if llm_text:
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=llm_text,
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

        extracted_syms, unknown_syms = self._extract_symbols(user_message)

        # 3. Actionable English / Hindi / Hinglish Paper Buy Order Preview (evaluated BEFORE portfolio summary)
        if not is_advisory and (has_buy_intent or has_sell_intent):
            if has_sell_intent:
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=self._build_clarification_reply("sell_or_mixed", lang, extracted_syms, active_sym),
                    language_detected=lang,
                    is_setup_incomplete=False,
                )

            target_syms = list(extracted_syms)
            if not target_syms and any(
                p in p_lower
                for p in (
                    "this stock",
                    "this share",
                    "active chart",
                    "current chart",
                    "is stock",
                    "ye share",
                    "yeh share",
                    "yeh stock",
                )
            ):
                target_syms = [active_sym]

            parsed_amt = self._extract_quantity_or_budget(user_message, p_lower)
            amt_mode = parsed_amt.get("mode")

            if amt_mode == "invalid_qty":
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=self._build_clarification_reply("invalid_qty", lang, target_syms, active_sym),
                    language_detected=lang,
                    is_setup_incomplete=False,
                )
            if not target_syms and unknown_syms:
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=self._build_clarification_reply(
                        "unknown_symbol", lang, target_syms, active_sym, extra=", ".join(unknown_syms)
                    ),
                    language_detected=lang,
                    is_setup_incomplete=False,
                )
            if not target_syms:
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=self._build_clarification_reply("missing_symbol", lang, target_syms, active_sym),
                    language_detected=lang,
                    is_setup_incomplete=False,
                )
            if amt_mode == "missing":
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=self._build_clarification_reply("missing_amount", lang, target_syms, active_sym),
                    language_detected=lang,
                    is_setup_incomplete=False,
                )

            if amt_mode == "quantity":
                if len(target_syms) > 1:
                    return AssistantMessageResponse(
                        message_id=msg_id,
                        conversation_id=conv_id,
                        reply=self._build_clarification_reply("ambiguous_symbols", lang, target_syms, active_sym),
                        language_detected=lang,
                        is_setup_incomplete=False,
                    )
                target_sym = target_syms[0]
                proposal = await self.tool_create_paper_proposal(
                    user_id,
                    [target_sym],
                    currency="INR",
                    conversation_id=conv_id,
                    db=db,
                    requested_quantities={target_sym: int(parsed_amt["quantity"])},
                )
                is_qty_order = True
            else:
                proposal = await self.tool_create_paper_proposal(
                    user_id,
                    target_syms,
                    budget=float(parsed_amt["budget"]),
                    currency="INR",
                    conversation_id=conv_id,
                    db=db,
                )
                is_qty_order = False

            prop_status = proposal.get("status")
            if prop_status == "PROPOSED":
                reply = self._format_proposal_preview_reply(proposal, lang, is_quantity_order=is_qty_order)
            elif prop_status == "INSUFFICIENT_BUDGET":
                budget_val = float(proposal.get("requested_budget") or 0)
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
            else:
                reply = proposal.get("error") or "Unable to prepare a virtual paper order preview."

            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                proposal=proposal,
                is_setup_incomplete=False,
            )

        # 4. Ambiguous symbol + portfolio message without clear action vs inquiry
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
        portfolio_inquiry_hints = (
            "balance",
            "cash",
            "holdings",
            "dikhao",
            "batao",
            "summary",
            "status",
            "equity",
            "value",
            "kitna",
            "kitne",
            "kya hai",
            "what is",
            "show",
            "check",
            "explain",
            "kya kya",
        )
        if (
            not is_advisory
            and not has_buy_intent
            and any(w in p_lower for w in portfolio_words)
            and extracted_syms
            and not any(h in p_lower for h in portfolio_inquiry_hints)
        ):
            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=self._build_clarification_reply("ambiguous_intent", lang, extracted_syms, active_sym),
                language_detected=lang,
                is_setup_incomplete=False,
            )

        # 5. Virtual Portfolio / Balance Inquiry
        if any(w in p_lower for w in portfolio_words) and not has_buy_intent:
            summary = await self.tool_get_my_paper_portfolio(user_id, currency="INR", db=db)
            reply = self._format_portfolio_summary_reply(summary, lang, active_sym)
            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                evidence_cards=[summary],
                is_setup_incomplete=False,
            )

        # 6. Chart Context Explanation (e.g. "explain this chart", "rsi", "chart samjhao", "moving average")
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
            target_sym = extracted_syms[0] if extracted_syms else active_sym

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

            if self.is_llm_ready():
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
                llm_text = await self.call_llm_api(user_message, sys_prompt)
                if llm_text:
                    reply = llm_text

            return AssistantMessageResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                reply=reply,
                language_detected=lang,
                evidence_cards=[chart_ctx],
                is_setup_incomplete=False,
            )

        # 6. Try Live LLM (Groq) if configured
        if self.is_llm_ready():
            sys_instruct = (
                "You are FinEx AI Paper Investment Assistant for Indian Equities (NSE). "
                f"Active chart context: {safe_chart_context}. "
                "Respond helpfully in the user's language (English, Hindi, or Hinglish). "
                "Maintain strict SEBI educational compliance: all trades and balances are 100% virtual paper trading. "
                "Ground all market prices and facts strictly using verified facts. Never invent quotes."
            )
            snapshots = await self.tool_get_market_snapshot([active_sym, "RELIANCE", "TCS", "HDFCBANK", "INFY"])
            context_notes = "\n".join([f"- {s['symbol']}: ₹{s['price']:,.2f} ({s['source']})" for s in snapshots])
            enhanced_sys = (
                f"{sys_instruct}\n\n"
                f"Current verified NSE quotes:\n{context_notes}\n\n"
                "If the user asks for 'best stock for tomorrow' or trading ideas: "
                "Do NOT give a blunt refusal. Provide an educational technical momentum screening guide for tomorrow: "
                "1. Note SEBI paper trading education. "
                "2. Give a 3-point technical checklist (5-day & 20-day SMA trend, RSI crossing 50, volume confirmation). "
                "3. Highlight 2-3 of the candidate stocks above with key technical pivot levels to watch."
            )
            llm_reply = await self.call_groq_api(user_message, enhanced_sys)

            if llm_reply:
                return AssistantMessageResponse(
                    message_id=msg_id,
                    conversation_id=conv_id,
                    reply=llm_reply,
                    language_detected=lang,
                    tool_calls=[],
                    evidence_cards=snapshots,
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
ai_assistant = gemini_assistant
AiInvestmentAssistant = GeminiInvestmentAssistant
