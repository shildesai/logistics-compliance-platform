from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    return HealthStatus(status="ok", service="logistics-compliance-api")
