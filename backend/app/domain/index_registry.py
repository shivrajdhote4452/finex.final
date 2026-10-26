"""Index Registry for Indian Equity Benchmark & Sectoral Indices.

Task: FinEx Implementing Indices
Defines canonical registry of Tier 1 (Headline) and Tier 2 (Sectoral) Indian market indices.
Registry-driven architecture: adding an index requires adding a single row here.
"""

from typing import Dict, List, Optional

INDEX_REGISTRY: List[Dict[str, str]] = [
    # =========================================================================
    # Tier 1 — Headline Indices
    # =========================================================================
    {
        "symbol": "NIFTY 50",
        "canonical_id": "NSE:NIFTY50",
        "display_name": "Nifty 50",
        "exchange": "NSE",
        "angel_token": "99926000",
        "yfinance_ticker": "^NSEI",
        "category": "headline",
        "tier": "1",
        "description": "Benchmark index representing the 50 largest and most liquid Indian companies listed on the NSE.",
        "currency": "INR",
    },
    {
        "symbol": "SENSEX",
        "canonical_id": "BSE:SENSEX",
        "display_name": "BSE Sensex",
        "exchange": "BSE",
        "angel_token": "99919000",
        "yfinance_ticker": "^BSESN",
        "category": "headline",
        "tier": "1",
        "description": "Benchmark index of 30 well-established and financially sound companies listed on BSE.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY BANK",
        "canonical_id": "NSE:BANKNIFTY",
        "display_name": "Nifty Bank",
        "exchange": "NSE",
        "angel_token": "99926009",
        "yfinance_ticker": "^NSEBANK",
        "category": "headline",
        "tier": "1",
        "description": "Index comprising the most capitalized and liquid Indian banking stocks.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY NEXT 50",
        "canonical_id": "NSE:NIFTYNXT50",
        "display_name": "Nifty Next 50",
        "exchange": "NSE",
        "angel_token": "99926013",
        "yfinance_ticker": "^NSMIDCP",
        "category": "headline",
        "tier": "1",
        "description": "Represents the 50 companies from Nifty 100 after excluding the Nifty 50 constituents.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY MIDCAP 50",
        "canonical_id": "NSE:NIFTYMID50",
        "display_name": "Nifty Midcap 50",
        "exchange": "NSE",
        "angel_token": "99926014",
        "yfinance_ticker": "^NSEMDCP50",
        "category": "headline",
        "tier": "1",
        "description": "Captures the movement and performance of the top 50 mid-sized capitalized companies.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY SMALLCAP 100",
        "canonical_id": "NSE:NIFTYSML100",
        "display_name": "Nifty Smallcap 100",
        "exchange": "NSE",
        "angel_token": "99926021",
        "yfinance_ticker": "^CNXSC",
        "category": "headline",
        "tier": "1",
        "description": "Reflects the behavior and performance of the small market capitalization segment on NSE.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY 100",
        "canonical_id": "NSE:NIFTY100",
        "display_name": "Nifty 100",
        "exchange": "NSE",
        "angel_token": "99926011",
        "yfinance_ticker": "^CNX100",
        "category": "headline",
        "tier": "1",
        "description": "Diversified 100-stock index representing major sectors of the Indian economy.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY 500",
        "canonical_id": "NSE:NIFTY500",
        "display_name": "Nifty 500",
        "exchange": "NSE",
        "angel_token": "99926012",
        "yfinance_ticker": "^CRSLDX",
        "category": "headline",
        "tier": "1",
        "description": "Broad market index representing top 500 companies listed on the NSE.",
        "currency": "INR",
    },
    # =========================================================================
    # Tier 2 — Sectoral Indices
    # =========================================================================
    {
        "symbol": "NIFTY IT",
        "canonical_id": "NSE:NIFTYIT",
        "display_name": "Nifty IT",
        "exchange": "NSE",
        "angel_token": "99926008",
        "yfinance_ticker": "^CNXIT",
        "category": "sectoral",
        "tier": "2",
        "description": "Tracks the performance of Indian Information Technology companies.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY AUTO",
        "canonical_id": "NSE:NIFTYAUTO",
        "display_name": "Nifty Auto",
        "exchange": "NSE",
        "angel_token": "99926005",
        "yfinance_ticker": "^CNXAUTO",
        "category": "sectoral",
        "tier": "2",
        "description": "Designed to reflect the behavior and performance of the Indian automobile sector.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY PHARMA",
        "canonical_id": "NSE:NIFTYPHARMA",
        "display_name": "Nifty Pharma",
        "exchange": "NSE",
        "angel_token": "99926016",
        "yfinance_ticker": "^CNXPHARMA",
        "category": "sectoral",
        "tier": "2",
        "description": "Tracks the performance of the pharmaceuticals and healthcare sector.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY FMCG",
        "canonical_id": "NSE:NIFTYFMCG",
        "display_name": "Nifty FMCG",
        "exchange": "NSE",
        "angel_token": "99926007",
        "yfinance_ticker": "^CNXFMCG",
        "category": "sectoral",
        "tier": "2",
        "description": "Comprises companies in Fast Moving Consumer Goods.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY METAL",
        "canonical_id": "NSE:NIFTYMETAL",
        "display_name": "Nifty Metal",
        "exchange": "NSE",
        "angel_token": "99926010",
        "yfinance_ticker": "^CNXMETAL",
        "category": "sectoral",
        "tier": "2",
        "description": "Reflects the behavior of companies involved in metals and mining.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY ENERGY",
        "canonical_id": "NSE:NIFTYENERGY",
        "display_name": "Nifty Energy",
        "exchange": "NSE",
        "angel_token": "99926006",
        "yfinance_ticker": "^CNXENERGY",
        "category": "sectoral",
        "tier": "2",
        "description": "Includes companies belonging to petroleum, gas, and power sectors.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY PSU BANK",
        "canonical_id": "NSE:NIFTYPSUBANK",
        "display_name": "Nifty PSU Bank",
        "exchange": "NSE",
        "angel_token": "99926017",
        "yfinance_ticker": "^CNXPSUBANK",
        "category": "sectoral",
        "tier": "2",
        "description": "Tracks the performance of Public Sector Banks in India.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY REALTY",
        "canonical_id": "NSE:NIFTYREALTY",
        "display_name": "Nifty Realty",
        "exchange": "NSE",
        "angel_token": "99926018",
        "yfinance_ticker": "^CNXREALTY",
        "category": "sectoral",
        "tier": "2",
        "description": "Comprises real estate development and construction companies.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY MEDIA",
        "canonical_id": "NSE:NIFTYMEDIA",
        "display_name": "Nifty Media",
        "exchange": "NSE",
        "angel_token": "99926015",
        "yfinance_ticker": "^CNXMEDIA",
        "category": "sectoral",
        "tier": "2",
        "description": "Reflects the behavior and performance of media and entertainment companies.",
        "currency": "INR",
    },
    {
        "symbol": "NIFTY FINANCIAL SERVICES",
        "canonical_id": "NSE:FINNIFTY",
        "display_name": "Nifty Financial Services",
        "exchange": "NSE",
        "angel_token": "99926037",
        "yfinance_ticker": "NIFTY_FIN_SERVICE.NS",
        "category": "sectoral",
        "tier": "2",
        "description": "Reflects the performance of banks, financial institutions, and housing finance companies.",
        "currency": "INR",
    },
]

# Quick lookup indexes
INDEX_BY_SYMBOL: Dict[str, Dict[str, str]] = {idx["symbol"].upper(): idx for idx in INDEX_REGISTRY}
INDEX_BY_CANONICAL: Dict[str, Dict[str, str]] = {idx["canonical_id"].upper(): idx for idx in INDEX_REGISTRY}


def get_index_by_symbol(symbol: str) -> Optional[Dict[str, str]]:
    """Look up an index by exact symbol, canonical id, or normalized name."""
    clean = symbol.strip().upper()
    if clean in INDEX_BY_SYMBOL:
        return INDEX_BY_SYMBOL[clean]
    if clean in INDEX_BY_CANONICAL:
        return INDEX_BY_CANONICAL[clean]

    # Partial / normalized match (e.g. NIFTY50 -> NIFTY 50, SENSEX -> SENSEX, BANKNIFTY -> NIFTY BANK)
    normalized = clean.replace(" ", "").replace("_", "").replace("-", "")
    for idx in INDEX_REGISTRY:
        reg_norm = idx["symbol"].replace(" ", "").replace("_", "").replace("-", "")
        if reg_norm == normalized:
            return idx
        can_norm = idx["canonical_id"].replace("NSE:", "").replace("BSE:", "").replace(" ", "")
        if can_norm == normalized:
            return idx
    return None
