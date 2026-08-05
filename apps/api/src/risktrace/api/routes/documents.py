from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.api.schemas.documents import DocumentDetail
from risktrace.core.demo import get_demo_tenant_id
from risktrace.db.models import RawDocument
from risktrace.db.session import get_db

router = APIRouter(prefix="/documents", tags=["documents"])
DemoTenantId = Annotated[UUID, Depends(get_demo_tenant_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: UUID,
    tenant_id: DemoTenantId,
    session: DbSession,
) -> DocumentDetail:
    doc = await session.scalar(
        select(RawDocument).where(
            RawDocument.id == document_id,
            RawDocument.tenant_id == tenant_id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")
    return DocumentDetail.model_validate(doc)
