import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.api.auth import IngestionPrincipal, get_ingestion_principal
from risktrace.db.session import get_db
from risktrace.ingestion.pipeline import DeterministicIngestionPipeline
from risktrace.ingestion.repository import (
    ImmutableSourceConflictError,
    SqlAlchemyIngestionRepository,
)
from risktrace.ingestion.schemas import IngestionResponse, SourceRecord
from risktrace.ingestion.service import IngestionService

router = APIRouter(prefix="/v1/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)

DbSession = Annotated[AsyncSession, Depends(get_db)]
Principal = Annotated[IngestionPrincipal, Depends(get_ingestion_principal)]


def get_ingestion_service(session: DbSession) -> IngestionService:
    return IngestionService(SqlAlchemyIngestionRepository(session))


Ingestion = Annotated[IngestionService, Depends(get_ingestion_service)]


def get_ingestion_pipeline(session: DbSession) -> DeterministicIngestionPipeline:
    return DeterministicIngestionPipeline(session)


Pipeline = Annotated[DeterministicIngestionPipeline, Depends(get_ingestion_pipeline)]


@router.post(
    "/items",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_item(
    record: SourceRecord,
    principal: Principal,
    service: Ingestion,
    pipeline: Pipeline,
    session: DbSession,
) -> IngestionResponse:
    if record.source.provider not in principal.allowed_providers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="source provider is outside this service account scope",
        )

    try:
        stored = await service.ingest(record, tenant_id=principal.tenant_id)
        if stored.outcome == "inserted":
            try:
                async with session.begin_nested():
                    await pipeline.process_document(stored.document_id)
            except Exception:
                logger.exception(
                    "deterministic enrichment failed for document %s",
                    stored.document_id,
                )
        await session.commit()
    except ImmutableSourceConflictError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="source identity already exists with different immutable content",
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return IngestionResponse(
        outcome=stored.outcome,
        document_id=stored.document_id,
        receipt_id=stored.receipt_id,
        duplicate_of_document_id=stored.duplicate_of_document_id,
        received_at=stored.received_at,
        processing_status="pending_enrichment",
    )
