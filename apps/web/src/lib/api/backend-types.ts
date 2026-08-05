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
  created_at: string;
  updated_at: string;
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
  source_url: string | null;
  engagement: Record<string, unknown> | null;
  raw_text_preview: string;
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
  mechanism: string;
  direction: string;
  horizon: string;
  evidence_ids: string[];
  knowledge_ids: string[];
  model_confidence: number;
  status: string;
  created_at: string;
};
