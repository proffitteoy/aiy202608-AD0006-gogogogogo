import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from risktrace.api.auth import get_ingestion_principal
from risktrace.core.config import Settings
from risktrace.ingestion.repository import StoredIngestion
from risktrace.ingestion.schemas import SourceRecord
from risktrace.ingestion.service import IngestionService
from risktrace.main import create_app


def source_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "external_id": "announcement-20260805-001",
        "source": {
            "provider": "licensed-disclosures",
            "stream": "announcements",
            "type": "fact",
            "level": "official",
            "collection_method": "authorized_api",
            "license_scope": "internal_research",
        },
        "published_at": "2026-08-05T09:30:00+08:00",
        "title": "Disclosure title",
        "content": "Disclosure body",
        "url": "https://example.com/disclosures/1",
        "metadata": {"author": "Issuer"},
    }
    payload.update(overrides)
    return payload


class RecordingStore:
    def __init__(self) -> None:
        self.values: dict[str, object] | None = None

    async def store(
        self,
        *,
        values: dict[str, object],
        provider: str,
        stream: str,
        received_at: datetime,
        replay_at: datetime | None,
    ) -> StoredIngestion:
        self.values = values
        assert provider == "licensed-disclosures"
        assert stream == "announcements"
        assert replay_at is None
        return StoredIngestion(
            outcome="inserted",
            document_id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
            receipt_id=uuid.UUID("20000000-0000-0000-0000-000000000001"),
            duplicate_of_document_id=None,
            received_at=received_at,
        )


def test_source_record_rejects_downstream_authority_fields() -> None:
    for field in ("tenant_id", "event_id", "sentiment", "risk", "topic"):
        with pytest.raises(ValidationError):
            SourceRecord.model_validate(source_payload(**{field: "not-source-data"}))

    with pytest.raises(ValidationError):
        SourceRecord.model_validate(source_payload(metadata={"risk_score": 0.8}))


def test_source_record_requires_timezone_and_matching_source_level() -> None:
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(source_payload(published_at="2026-08-05T09:30:00"))

    payload = source_payload()
    source = payload["source"]
    assert isinstance(source, dict)
    source["level"] = "professional_media"
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(payload)


@pytest.mark.asyncio
async def test_ingestion_service_normalizes_utc_without_faking_engagement() -> None:
    received_at = datetime(2026, 8, 5, 4, 0, tzinfo=UTC)
    store = RecordingStore()
    service = IngestionService(store, now=lambda: received_at)
    tenant_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    await service.ingest(SourceRecord.model_validate(source_payload()), tenant_id=tenant_id)

    assert store.values is not None
    assert store.values["tenant_id"] == tenant_id
    assert store.values["published_at"] == datetime(2026, 8, 5, 1, 30, tzinfo=UTC)
    assert store.values["collected_at"] == received_at
    assert store.values["received_at"] == received_at
    assert store.values["engagement"] == {}
    metadata = store.values["source_metadata"]
    assert isinstance(metadata, dict)
    ingestion_metadata = metadata["_risktrace_ingestion"]
    assert isinstance(ingestion_metadata, dict)
    assert ingestion_metadata["engagement_available"] is False


def test_ingestion_principal_is_server_owned_and_provider_scoped() -> None:
    tenant_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    settings = Settings(
        ingestion_api_token="test-token",
        ingestion_tenant_id=tenant_id,
        ingestion_allowed_providers="licensed-disclosures,licensed-news",
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

    principal = get_ingestion_principal(credentials, settings)

    assert principal.tenant_id == tenant_id
    assert principal.allowed_providers == frozenset(
        {"licensed-disclosures", "licensed-news"}
    )

    with pytest.raises(HTTPException) as exc_info:
        get_ingestion_principal(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-token"),
            settings,
        )
    assert exc_info.value.status_code == 401


def test_openapi_exposes_ingestion_without_tenant_or_authority_fields() -> None:
    schema = create_app().openapi()
    operation = schema["paths"]["/api/v1/ingestion/items"]["post"]
    source_record = schema["components"]["schemas"]["SourceRecord"]

    assert operation["security"] == [{"HTTPBearer": []}]
    assert {
        "tenant_id",
        "event_id",
        "sentiment",
        "risk",
        "topic",
    }.isdisjoint(source_record["properties"])


def test_source_record_converts_non_utc_offset() -> None:
    record = SourceRecord.model_validate(
        source_payload(collected_at="2026-08-05T10:00:00+08:00")
    )

    assert record.collected_at == datetime(2026, 8, 5, 2, 0, tzinfo=UTC)
    assert record.published_at.utcoffset() == timedelta(0)
