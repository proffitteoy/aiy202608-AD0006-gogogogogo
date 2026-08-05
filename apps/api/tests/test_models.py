from risktrace.db.base import Base
from risktrace.db.models import (
    Entity,
    Event,
    EventAdmissionRecord,
    EventDocument,
    EventMetric,
    EventScoreCalibration,
    EvidenceLink,
    IngestionReceipt,
    OpinionRecord,
    PlatformBaseline,
    RawDocument,
    SourceCheckpoint,
    SourceHealth,
    TransmissionEdge,
)


def test_core_traceability_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "entities",
        "event_admission_records",
        "event_documents",
        "event_metrics",
        "event_score_calibrations",
        "events",
        "evidence_links",
        "ingestion_receipts",
        "opinion_records",
        "platform_baselines",
        "raw_documents",
        "source_checkpoints",
        "source_health",
        "transmission_edges",
    }


def test_raw_document_keeps_source_and_collection_provenance() -> None:
    columns = RawDocument.__table__.columns
    for required_column in (
        "source_id",
        "source_url",
        "source_level",
        "published_at",
        "collected_at",
        "received_at",
        "replay_at",
        "collection_method",
        "license_scope",
        "content_hash",
        "raw_payload_ref",
        "source_metadata",
    ):
        assert required_column in columns

    assert Event.__table__.columns["tenant_id"].nullable is False
    assert Entity.__table__.columns["tenant_id"].nullable is False
    assert EventDocument.__table__.columns["document_id"].primary_key is True
    assert EvidenceLink.__table__.columns["tenant_id"].nullable is False
    assert IngestionReceipt.__table__.columns["tenant_id"].nullable is False
    assert SourceCheckpoint.__table__.columns["tenant_id"].nullable is False
    assert SourceHealth.__table__.columns["tenant_id"].nullable is False


def test_event_engine_tables_keep_versions_inputs_and_tenant_scope() -> None:
    event_columns = Event.__table__.columns
    for required_column in (
        "last_seen_at",
        "centroid_embedding",
        "centroid_weight",
        "embedding_model",
        "admission_decision_value",
        "heat_score",
        "momentum",
        "raw_score",
        "calibrated_score",
        "score_confidence",
        "score_lower_bound",
        "score_upper_bound",
        "scoring_version",
        "calibration_version",
        "evidence_count",
    ):
        assert required_column in event_columns

    assert EventAdmissionRecord.__table__.columns["rule_version"].nullable is False
    assert EventAdmissionRecord.__table__.columns["tenant_id"].nullable is False
    assert EventMetric.__table__.columns["calculation_id"].primary_key is True
    assert EventMetric.__table__.columns["input_document_ids"].nullable is False
    assert EventAdmissionRecord.__table__.columns["decision_value"].nullable is False
    assert EventAdmissionRecord.__table__.columns["data_completeness"].nullable is False
    assert EventMetric.__table__.columns["scoring_version"].nullable is False
    assert EventMetric.__table__.columns["raw_score"].nullable is True
    assert PlatformBaseline.__table__.columns["tenant_id"].nullable is False


def test_opinion_record_fields() -> None:
    columns = OpinionRecord.__table__.columns
    assert columns["tenant_id"].nullable is False
    assert columns["event_id"].nullable is False
    assert columns["document_id"].nullable is False
    assert columns["stance"].nullable is False
    assert columns["emotion"].nullable is False
    assert columns["reason"].nullable is False
    assert columns["claim_type"].nullable is False
    assert columns["evidence_span"].nullable is False
    assert columns["model_confidence"].nullable is False
    assert columns["model_version"].nullable is False
    assert columns["prompt_version"].nullable is False
    assert columns["input_hash"].nullable is False


def test_transmission_edge_fields() -> None:
    columns = TransmissionEdge.__table__.columns
    assert columns["tenant_id"].nullable is False
    assert columns["event_id"].nullable is False
    assert columns["from_node_type"].nullable is False
    assert columns["from_node_id"].nullable is False
    assert columns["to_node_type"].nullable is False
    assert columns["to_node_id"].nullable is False
    assert columns["mechanism"].nullable is False
    assert columns["direction"].nullable is False
    assert columns["horizon"].nullable is False
    assert columns["model_confidence"].nullable is False
    assert columns["status"].nullable is False
    assert columns["model_version"].nullable is False
    assert columns["prompt_version"].nullable is False
    assert columns["input_hash"].nullable is False


def test_score_calibration_keeps_rule3_inputs_and_degradation_state() -> None:
    columns = EventScoreCalibration.__table__.columns
    for required_column in (
        "calculation_id",
        "tenant_id",
        "event_id",
        "score_calculation_id",
        "snapshot_at",
        "scoring_version",
        "calibration_version",
        "raw_score",
        "calibrated_score",
        "confidence",
        "lower_bound",
        "upper_bound",
        "data_completeness",
        "source_health",
        "market_data_completeness",
        "input_evidence_ids",
        "evidence_snapshot_hash",
        "monte_carlo_seed",
        "sample_count",
        "parameters",
        "calculation_status",
        "degradation_reasons",
    ):
        assert required_column in columns

    assert columns["calculation_id"].primary_key is True
    assert columns["tenant_id"].nullable is False
    assert columns["lower_bound"].nullable is False
    assert columns["market_data_completeness"].nullable is True
    assert "updated_at" not in columns
