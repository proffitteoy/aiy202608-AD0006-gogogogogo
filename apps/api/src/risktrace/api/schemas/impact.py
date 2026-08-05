import uuid

from pydantic import BaseModel


class ImpactRowItem(BaseModel):
    entity_id: uuid.UUID
    entity_name: str
    entity_type: str
    direction: str
    impact_strength: float
    business_exposure: float
    opinion_support: float
    fact_support: float
    time_horizon: str
    composite_confidence: float
    edge_count: int
    opinion_count: int
    evidence_count: int

    model_config = {"from_attributes": True}


class ImpactMatrixResponse(BaseModel):
    items: list[ImpactRowItem]
    total: int
