"""AI Portfolio & Sourced Security Comparison Router.

Task ID: S3-AI-01, S3-AI-02
Exposes:
- GET /ai/compare: Side-by-side sourced company comparison with zero invented metrics.
- GET /ai/portfolios/{id}/explain: Deterministic portfolio concentration and diversification explainer.
"""

from backend.app.adapters.market_data_provider import VERIFIED_OBSERVATIONS
from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import ForbiddenException, NotFoundException
from backend.app.domain.company_comparison import compare_securities
from backend.app.domain.portfolio import calculate_portfolio_valuation
from backend.app.domain.portfolio_explainer import generate_portfolio_explanation
from backend.app.routers.auth import get_current_user_id
from backend.app.routers.portfolio import _PORTFOLIO_STORE
from fastapi import APIRouter, Depends, Query, Request

router = APIRouter(prefix="/ai", tags=["AI Intelligence & Reasoning"])


@router.get("/compare")
async def get_security_comparison(
    request: Request,
    symbol_a: str = Query(..., description="First security ticker (e.g. RELIANCE)"),
    symbol_b: str = Query(..., description="Second security ticker (e.g. TCS)"),
):
    """Compare two securities side-by-side using authentic sourced market data.

    Guarantees:
    - Missing metrics are explicitly disclosed as 'not available' with source and date.
    - Zero fabricated financial ratios or invented prices.
    - Full educational disclaimer.
    """
    cid = getattr(request.state, "correlation_id", None)
    result = compare_securities(symbol_a, symbol_b)

    if not result:
        raise NotFoundException(
            message=f"One or both securities ('{symbol_a}', '{symbol_b}') are not found in verified market data registry."
        )

    return create_response_envelope(data=result.model_dump(mode="json"), correlation_id=cid)


@router.get("/portfolios/{portfolio_id}/explain")
async def explain_portfolio_diversification(
    request: Request,
    portfolio_id: str,
    current_user: dict = Depends(get_current_user_id),
):
    """Generate educational concentration and diversification narrative from deterministic metrics.

    Guarantees:
    - No arithmetic delegated to LLM.
    - Frozen snapshot binding.
    - Strict user ownership enforcement.
    """
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    p = _PORTFOLIO_STORE.get(portfolio_id)
    if not p:
        raise NotFoundException(message="Portfolio not found.")
    if p["user_id"] != user_id:
        raise ForbiddenException(message="Forbidden: You do not own this portfolio.")

    quotes = {sym: obs["price"] for sym, obs in VERIFIED_OBSERVATIONS.items()}
    sectors = {
        "RELIANCE": "Energy & Retail",
        "TCS": "Technology",
        "INFY": "Technology",
        "HDFCBANK": "Banking & Financial Services",
        "ICICIBANK": "Banking & Financial Services",
        "TATAMOTORS": "Automobile",
        "SBIN": "Banking & Financial Services",
        "ITC": "Consumer Goods & FMCG",
    }

    summary = calculate_portfolio_valuation(
        portfolio_id=portfolio_id,
        holdings=p["holdings"],
        quotes=quotes,
        sectors=sectors,
        currency=p.get("currency", "INR"),
    )

    explanation = generate_portfolio_explanation(summary)

    return create_response_envelope(data=explanation.model_dump(mode="json"), correlation_id=cid)
