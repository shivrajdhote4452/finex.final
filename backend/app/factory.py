from contextlib import asynccontextmanager
from typing import Optional

from backend.app.config import Settings, get_settings
from backend.app.core.errors import (
    FinExException,
    finex_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from backend.app.core.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from backend.app.routers.ai_chat import router as ai_chat_router
from backend.app.routers.ai_portfolio import router as ai_portfolio_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.auth import users_router
from backend.app.routers.health import router as health_router
from backend.app.routers.market import router as market_router
from backend.app.routers.portfolio import router as portfolio_router
from backend.app.routers.risk import router as risk_router
from backend.app.routers.sample import router as sample_router
from backend.app.routers.watchlists import router as watchlists_router
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """
    FastAPI Application Factory.
    Initializes configuration, registers middlewares, exception handlers, and API routers.
    """
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup phase
        app.state.settings = app_settings
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

    # 1. Custom Middlewares
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
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
    app.include_router(ai_portfolio_router, prefix=v1_prefix)
    app.include_router(ai_chat_router, prefix=v1_prefix)
    app.include_router(sample_router, prefix=v1_prefix)

    return app
