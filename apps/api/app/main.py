from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Phase 1 application shell for the Logistics Compliance Intelligence "
        "Platform. Serves synthetic dashboard data only — see "
        "docs/IMPLEMENTATION_PLAN.md for the phased build-out of real "
        "compliance logic."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Unversioned infra health check.
app.include_router(health.router)
# Versioned product API.
app.include_router(api_router, prefix=settings.api_v1_prefix)
