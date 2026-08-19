from fastapi import APIRouter

from app.api.v1.endpoints import dashboard, me, operations, organisation

api_router = APIRouter()
api_router.include_router(me.router)
api_router.include_router(organisation.router)
api_router.include_router(operations.router)
api_router.include_router(dashboard.router)
