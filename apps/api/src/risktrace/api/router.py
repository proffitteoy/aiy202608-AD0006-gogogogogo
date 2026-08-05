from fastapi import APIRouter

from risktrace.api.routes.documents import router as documents_router
from risktrace.api.routes.events import router as events_router
from risktrace.api.routes.health import router as health_router
from risktrace.api.routes.impact import router as impact_router
from risktrace.api.routes.ingestion import router as ingestion_router
from risktrace.api.routes.opinions import router as opinions_router
from risktrace.api.routes.pipeline import router as pipeline_router
from risktrace.api.routes.reports import router as reports_router
from risktrace.api.routes.transmission import router as transmission_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(ingestion_router)
api_router.include_router(events_router)
api_router.include_router(documents_router)
api_router.include_router(opinions_router)
api_router.include_router(transmission_router)
api_router.include_router(impact_router)
api_router.include_router(pipeline_router)
api_router.include_router(reports_router)
