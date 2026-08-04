from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from risktrace.api.schemas.documents import DocumentDetail
from risktrace.db.models import RawDocument
from risktrace.db.session import get_db

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    doc = await session.get(RawDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档未找到")
    return DocumentDetail.model_validate(doc)
