import uuid
from datetime import datetime

from pydantic import BaseModel


class OpinionItem(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    target_entity_id: uuid.UUID | None
    stance: str
    emotion: str
    reason: str
    claim_type: str
    evidence_span: str
    model_confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}


class OpinionListResponse(BaseModel):
    items: list[OpinionItem]
    total: int


class TransmissionEdgeItem(BaseModel):
    id: uuid.UUID
    from_node_type: str
    from_node_id: uuid.UUID
    to_node_type: str
    to_node_id: uuid.UUID
    from_node_label: str | None = None
    to_node_label: str | None = None
    mechanism: str
    direction: str
    horizon: str
    evidence_ids: list[uuid.UUID]
    knowledge_ids: list[uuid.UUID]
    model_confidence: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TransmissionListResponse(BaseModel):
    items: list[TransmissionEdgeItem]
    total: int
