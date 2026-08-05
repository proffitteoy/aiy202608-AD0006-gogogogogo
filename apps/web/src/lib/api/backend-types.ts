/**
 * 后端 FastAPI 返回的 raw schema。与 apps/api/src/risktrace/api/schemas/* 对齐。
 * 仅在 adapter 层可见，业务组件不直接依赖。
 */

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
};

export type BackendEventSummary = {
  id: string;
  title: string;
  status: string;
  first_published_at: string;
  document_count: number;
  source_breakdown: Record<string, number>;
  latest_activity: string | null;
  score: BackendEventScore;
  created_at: string;
  updated_at: string;
};

export type BackendEventScore = {
  status: "complete" | "degraded" | "unavailable";
  raw_score: number | null;
  calibrated_score: number | null;
  confidence: number | null;
  score_interval: {
    lower_bound: number;
    upper_bound: number;
  } | null;
  scoring_version: string | null;
  calibration_version: string | null;
  calculation_id: string | null;
  score_calculation_id: string | null;
  degradation_reasons: string[];
};

export type BackendTimelineBucket = {
  bucket_start: string;
  bucket_end: string;
  counts: Record<string, number>;
};

export type BackendLinkedDocument = {
  id: string;
  title: string | null;
  source_type: string;
  platform: string;
  published_at: string;
  weight: number;
  engagement: Record<string, unknown> | null;
};

export type BackendWorkspaceResponse = {
  event: BackendEventSummary;
  timeline: BackendTimelineBucket[];
  linked_documents: BackendLinkedDocument[];
};

export type BackendEvidenceItem = {
  id: string;
  title: string | null;
  source_type: string;
  platform: string;
  published_at: string;
  collected_at: string;
  source_url: string | null;
  engagement: Record<string, unknown> | null;
  raw_text_preview: string;
  collection_method: string;
  license_scope: string;
};

export type BackendOpinionItem = {
  id: string;
  document_id: string;
  target_entity_id: string | null;
  stance: string;
  emotion: string;
  reason: string;
  claim_type: string;
  evidence_span: string;
  model_confidence: number;
  created_at: string;
};

export type BackendTransmissionEdge = {
  id: string;
  from_node_type: string;
  from_node_id: string;
  to_node_type: string;
  to_node_id: string;
  from_node_label: string | null;
  to_node_label: string | null;
  mechanism: string;
  direction: string;
  horizon: string;
  evidence_ids: string[];
  knowledge_ids: string[];
  model_confidence: number;
  status: string;
  created_at: string;
};

export type BackendImpactMatrixRow = {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  direction: string;
  impact_strength: number;
  business_exposure: number;
  opinion_support: number;
  fact_support: number;
  time_horizon: string;
  composite_confidence: number;
  edge_count: number;
  opinion_count: number;
  evidence_count: number;
  evidence_ids: string[];
};

export type BackendReportStatementItem = {
  id: string;
  text: string;
  evidence_ids: string[];
  calculation_ids: string[];
};

export type BackendReportSectionItem = {
  id: string;
  title: string;
  status: string;
  items: BackendReportStatementItem[];
};

export type BackendReportSnapshotSummary = {
  id: string;
  event_id: string;
  snapshot_at: string;
  analysis_version: string;
  score_status: string;
  evidence_count: number;
  source_count: number;
  scoring_version: string | null;
  calibration_version: string | null;
};

export type BackendReportEventSummary = {
  id: string;
  title: string;
  status: string;
  first_published_at: string;
  source_count: number;
  authoritative_source_count: number;
  source_breakdown: Record<string, number>;
  score: BackendEventScore;
};

export type BackendReportCreateResponse = {
  id: string;
  event_id: string;
  snapshot_id: string;
  format: string;
  status: string;
  created_at: string;
};

export type BackendReportDetail = {
  id: string;
  event_id: string;
  snapshot_id: string;
  format: string;
  status: string;
  title: string;
  summary: string;
  render_engine: string;
  brief_prompt_version: string;
  body_html: string;
  evidence_ids: string[];
  calculation_ids: string[];
  degradation_reasons: string[];
  created_at: string;
  snapshot: BackendReportSnapshotSummary;
  event: BackendReportEventSummary;
  sections: BackendReportSectionItem[];
  evidence: BackendEvidenceItem[];
};
