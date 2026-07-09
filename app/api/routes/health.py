from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_health_service
from app.api.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(health_service: HealthService = Depends(get_health_service)) -> HealthResponse:
    status_value = health_service.check()
    return HealthResponse(**status_value.__dict__)


@router.get("/health/ready", response_model=HealthResponse)
def readiness_check(
    response: Response,
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    status_value = health_service.check()
    if not status_value.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(**status_value.__dict__)
