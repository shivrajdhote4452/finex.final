from contextlib import asynccontextmanager
from typing import Optional

from backend.app.config import Settings, get_settings
from backend.app.core.errors import (
    FinExException,
    finex_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from backend.app.core.middleware import (
    CorrelationIdMiddleware,
    RateLimiterMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from backend.app.routers.ai_chat import router as ai_chat_router
from backend.app.routers.ai_portfolio import router as ai_portfolio_router
from backend.app.routers.alerts import router as alerts_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.auth import users_router
from backend.app.routers.charts import router as charts_router
from backend.app.routers.gemini_assistant import router as gemini_assistant_router
from backend.app.routers.goals import router as goals_router
from backend.app.routers.health import router as health_router
from backend.app.routers.market import router as market_router
from backend.app.routers.notifications import router as notifications_router
from backend.app.routers.paper_trading import router as paper_trading_router
from backend.app.routers.portfolio import router as portfolio_router
from backend.app.routers.portfolio_intelligence import router as portfolio_intelligence_router
from backend.app.routers.risk import router as risk_router
from backend.app.routers.sample import router as sample_router
from backend.app.routers.spending import router as spending_router
from backend.app.routers.watchlists import router as watchlists_router
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """
    FastAPI Application Factory.
    Initializes configuration, registers middlewares, exception handlers, and API routers.
    """
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup phase: Ensure seed identities exist in PostgreSQL
        app.state.settings = app_settings
        try:
            from backend.app.domain.user_store import user_store

            await user_store.ensure_seed_users_db()
        except Exception:
            # Continue if DB is offline during unit testing
            pass
        try:
            from ai.rag.ingestion import ensure_documents_indexed_db

            await ensure_documents_indexed_db()
        except Exception:
            pass
        try:
            from backend.app.adapters.market_data_provider import ensure_market_quotes_seeded_db

            await ensure_market_quotes_seeded_db()
        except Exception:
            pass

        # Angel One SmartAPI live market data initialization
        if app_settings.MARKET_DATA_MODE == "INDIAN_LIVE_DATA":
            from backend.app.services.angel_adapter import AngelOneMarketAdapter

            angel = AngelOneMarketAdapter()
            if not angel.is_configured():
                raise RuntimeError("INDIAN_LIVE_DATA requires valid Angel One credentials")
            angel.authenticate()
            app.state.angel_adapter = angel
        yield
        # Shutdown phase

    app = FastAPI(
        title=app_settings.APP_NAME,
        version="0.1.0",
        description="FinEx - Educational Financial Platform API",
        openapi_url=f"{app_settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{app_settings.API_V1_PREFIX}/docs",
        redoc_url=f"{app_settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    app.state.settings = app_settings

    # 1. Custom Security & Observability Middlewares (Outer to Inner)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RateLimiterMiddleware, default_limit=150, auth_limit=40)
    app.add_middleware(CorrelationIdMiddleware)

    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            "X-Correlation-ID",
            "X-Request-ID",
            "X-Response-Time-Ms",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
        ],
    )

    # 3. Exception Handlers
    app.add_exception_handler(FinExException, finex_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 4. Mount API v1 Routers
    v1_prefix = app_settings.API_V1_PREFIX
    app.include_router(health_router, prefix=v1_prefix)
    app.include_router(auth_router, prefix=v1_prefix)
    app.include_router(users_router, prefix=v1_prefix)
    app.include_router(risk_router, prefix=v1_prefix)
    app.include_router(market_router, prefix=v1_prefix)
    app.include_router(watchlists_router, prefix=v1_prefix)
    app.include_router(portfolio_router, prefix=v1_prefix)
    app.include_router(paper_trading_router, prefix=v1_prefix)
    app.include_router(ai_portfolio_router, prefix=v1_prefix)
    app.include_router(ai_chat_router, prefix=v1_prefix)
    app.include_router(gemini_assistant_router, prefix=v1_prefix)
    app.include_router(alerts_router, prefix=v1_prefix)
    app.include_router(notifications_router, prefix=v1_prefix)
    app.include_router(portfolio_intelligence_router, prefix=v1_prefix)
    app.include_router(goals_router, prefix=v1_prefix)
    app.include_router(charts_router, prefix=v1_prefix)
    app.include_router(spending_router, prefix=v1_prefix)
    app.include_router(sample_router, prefix=v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url=f"{app_settings.API_V1_PREFIX}/docs")

    @app.get("/docs", include_in_schema=False)
    async def docs_redirect():
        return RedirectResponse(url=f"{app_settings.API_V1_PREFIX}/docs")

    return app
