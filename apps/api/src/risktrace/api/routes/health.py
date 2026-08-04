from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from risktrace import __version__
from risktrace.core.health import DependencyCheck, InfrastructureHealthService

router = APIRouter(prefix="/health", tags=["health"])


class DependencyStatus(BaseModel):
    status: str
    latency_ms: float
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    dependencies: dict[str, DependencyStatus] | None = None


def get_health_service(request: Request) -> InfrastructureHealthService:
    return request.app.state.health_service


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(
        status="alive",
        service="risktrace-api",
        version=__version__,
        timestamp=datetime.now(UTC),
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    response: Response,
    health_service: InfrastructureHealthService = Depends(get_health_service),
) -> HealthResponse:
    checks: dict[str, DependencyCheck] = await health_service.readiness()
    is_ready = all(check.status == "up" for check in checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ready" if is_ready else "degraded",
        service="risktrace-api",
        version=__version__,
        timestamp=datetime.now(UTC),
        dependencies={
            name: DependencyStatus(
                status=check.status,
                latency_ms=check.latency_ms,
                detail=check.detail,
            )
            for name, check in checks.items()
        },
    )
