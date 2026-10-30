from typing import Any, Callable, Dict, Optional

from backend.app.core.envelope import create_response_envelope
from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

# Health checker hook that can be set or overridden by DB connector / tests
_database_health_checker: Optional[Callable[[], Any]] = None


def set_database_health_checker(checker: Optional[Callable[[], Any]]):
    global _database_health_checker
    _database_health_checker = checker


async def check_db_ready() -> Dict[str, Any]:
    """Execute registered database health check or report status."""
    global _database_health_checker
    if _database_health_checker is not None:
        try:
            res = _database_health_checker()
            if hasattr(res, "__await__"):
                res = await res
            return {"status": "ok", "details": res}
        except Exception as e:
            return {"status": "down", "error": str(e)}

    try:
        from backend.app.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database ping succeeded"}
    except Exception as e:
        return {"status": "down", "error": f"{type(e).__name__}: {str(e)}"}


class LivenessData(BaseModel):
    status: str = Field("ok", description="Process liveness indicator")
    app: str = Field(..., description="Application name")
    environment: str = Field(..., description="Active environment name")
    version: str = Field("v1.2.1-live-resilience", description="Deployed build signature")


class ReadinessData(BaseModel):
    status: str = Field(..., description="Overall readiness: ok or degraded")
    dependencies: Dict[str, Any] = Field(..., description="Status of required dependencies")


@router.get(
    "/live",
    summary="Process Liveness Probe",
    description="Returns 200 when the FastAPI application process is alive and responding.",
)
@router.get(
    "/healthz",
    include_in_schema=False,
)
async def get_liveness(request: Request):
    settings = request.app.state.settings
    cid = getattr(request.state, "correlation_id", "none")
    data = LivenessData(
        status="ok",
        app=settings.APP_NAME,
        environment=settings.ENVIRONMENT.value,
        version="v1.2.1-live-resilience",
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)


@router.get(
    "/ready",
    summary="Dependency Readiness Probe",
    description="Returns 200 when all required backing dependencies are healthy; 503 if any critical dependency is down.",
)
@router.get(
    "/readyz",
    include_in_schema=False,
)
async def get_readiness(request: Request, response: Response):
    cid = getattr(request.state, "correlation_id", "none")
    db_status = await check_db_ready()

    is_ready = db_status.get("status") == "ok"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    data = ReadinessData(
        status="ok" if is_ready else "degraded",
        dependencies={
            "database": db_status.get("status"),
        },
    )
    return create_response_envelope(data.model_dump(), correlation_id=cid)
