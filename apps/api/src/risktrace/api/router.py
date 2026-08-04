from fastapi import APIRouter

from risktrace.api.routes.documents import router as documents_router
from risktrace.api.routes.events import router as events_router
from risktrace.api.routes.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(events_router)
api_router.include_router(documents_router)
