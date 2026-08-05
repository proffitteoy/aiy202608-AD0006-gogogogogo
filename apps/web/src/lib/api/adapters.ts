import type {
  Availability,
  EventDetail,
  EventScore,
  EventSummary,
  EvidenceItem,
  OpinionAttribution,
  TimelinePoint,
  TransmissionEdge,
  TransmissionGraph,
  TransmissionNode,
  TransmissionNodeType,
} from "@/lib/types";

import type {
  BackendEventScore,
  BackendEventSummary,
  BackendEvidenceItem,
  BackendOpinionItem,
  BackendTransmissionEdge,
  BackendWorkspaceResponse,
} from "./backend-types";

function sourceTierOf(sourceType: string): EvidenceItem["sourceTier"] {
  const type = sourceType.toLowerCase();
  if (type === "fact") return "authoritative";
  if (type === "news") return "media";
  if (type === "market") return "market";
  return "social";
}

function emotionToSentiment(emotion: string): number | null {
  const value = emotion.toLowerCase();
  if (value.includes("positive") || value.includes("optimistic")) return 0.5;
  if (
    value.includes("negative") ||
    value.includes("pessimistic") ||
    value.includes("angry")
  ) {
    return -0.5;
  }
  if (value.includes("neutral")) return 0;
  return null;
}

function adaptScore(raw: BackendEventScore): EventScore {
  return {
    status: raw.status,
    rawScore: raw.raw_score,
    calibratedScore: raw.calibrated_score,
    confidence: raw.confidence,
    scoreInterval: raw.score_interval
      ? {
          lowerBound: raw.score_interval.lower_bound,
          upperBound: raw.score_interval.upper_bound,
        }
      : null,
    scoringVersion: raw.scoring_version,
    calibrationVersion: raw.calibration_version,
    calculationId: raw.calculation_id,
    scoreCalculationId: raw.score_calculation_id,
    degradationReasons: raw.degradation_reasons,
  };
}

export function adaptEventSummary(raw: BackendEventSummary): EventSummary {
  return {
    id: raw.id,
    title: raw.title,
    status: raw.status,
    publishedAt: raw.first_published_at,
    sourceCount: raw.document_count,
    authoritativeSourceCount: raw.source_breakdown.fact ?? 0,
    sourceBreakdown: raw.source_breakdown,
    score: adaptScore(raw.score),
    freshness: {
      updatedAt: raw.latest_activity ?? raw.updated_at,
    },
  };
}

function adaptTimeline(
  workspace: BackendWorkspaceResponse,
  opinions: BackendOpinionItem[],
): TimelinePoint[] {
  const publishedAtByDocument = new Map(
    workspace.linked_documents.map((document) => [
      document.id,
      document.published_at,
    ]),
  );

  return workspace.timeline.map((bucket, index) => {
    const bucketStart = new Date(bucket.bucket_start).getTime();
    const bucketEnd = new Date(bucket.bucket_end).getTime();
    const documents = workspace.linked_documents.filter((document) => {
      const timestamp = new Date(document.published_at).getTime();
      return timestamp >= bucketStart && timestamp < bucketEnd;
    });
    const sentiments = opinions
      .filter((opinion) => {
        const publishedAt = publishedAtByDocument.get(opinion.document_id);
        if (!publishedAt) return false;
        const timestamp = new Date(publishedAt).getTime();
        return timestamp >= bucketStart && timestamp < bucketEnd;
      })
      .map((opinion) => emotionToSentiment(opinion.emotion))
      .filter((value): value is number => value !== null);

    return {
      id: `bucket_${index}`,
      timestamp: bucket.bucket_start,
      documentCount: Object.values(bucket.counts).reduce(
        (sum, count) => sum + count,
        0,
      ),
      sentiment:
        sentiments.length > 0
          ? sentiments.reduce((sum, value) => sum + value, 0) /
            sentiments.length
          : null,
      label: index === 0 && documents.length > 0 ? "首条证据" : undefined,
      evidenceIds: documents.map((document) => document.id),
    };
  });
}

function adaptOpinions(
  opinions: BackendOpinionItem[],
  evidence: BackendEvidenceItem[],
): OpinionAttribution[] {
  const evidenceById = new Map(evidence.map((item) => [item.id, item]));
  return opinions.map((opinion) => {
    const document = evidenceById.get(opinion.document_id);
    return {
      id: opinion.id,
      stance: opinion.stance,
      emotion: opinion.emotion,
      reason: opinion.reason,
      claimType: opinion.claim_type,
      confidence: opinion.model_confidence,
      excerpt: opinion.evidence_span,
      source: document?.platform ?? "来源未解析",
      publishedAt: document?.published_at ?? opinion.created_at,
      authoritative: document?.source_type === "fact",
      evidenceIds: [opinion.document_id],
    };
  });
}

function nodeType(value: string): TransmissionNodeType {
  const normalized = value.toLowerCase();
  if (normalized.includes("sector") || normalized.includes("industry")) {
    return "sector";
  }
  if (normalized.includes("event")) return "event";
  return "entity";
}

function adaptTransmission(edges: BackendTransmissionEdge[]): TransmissionGraph {
  const nodes = new Map<string, TransmissionNode>();
  const adaptedEdges: TransmissionEdge[] = [];

  for (const edge of edges) {
    nodes.set(edge.from_node_id, {
      id: edge.from_node_id,
      label: edge.from_node_label ?? "未解析主体",
      type: nodeType(edge.from_node_type),
    });
    nodes.set(edge.to_node_id, {
      id: edge.to_node_id,
      label: edge.to_node_label ?? "未解析主体",
      type: nodeType(edge.to_node_type),
    });
    adaptedEdges.push({
      id: edge.id,
      source: edge.from_node_id,
      target: edge.to_node_id,
      confidence: edge.model_confidence,
      status: edge.status,
      mechanism: edge.mechanism,
      direction: edge.direction,
      horizon: edge.horizon,
      evidenceIds: edge.evidence_ids,
    });
  }

  return { nodes: Array.from(nodes.values()), edges: adaptedEdges };
}

function adaptEvidence(items: BackendEvidenceItem[]): EvidenceItem[] {
  return items.map((item) => ({
    id: item.id,
    source: item.platform || item.source_type,
    sourceTier: sourceTierOf(item.source_type),
    publishedAt: item.published_at,
    title: item.title ?? "（无标题）",
    body: item.raw_text_preview,
    citedSpans: [],
    linkUrl: item.source_url ?? undefined,
    capturedAt: item.collected_at,
    collectionMethod: item.collection_method,
    licenseScope: item.license_scope,
  }));
}

export function adaptEventDetail(input: {
  workspace: BackendWorkspaceResponse;
  evidence: BackendEvidenceItem[];
  opinions: BackendOpinionItem[];
  transmission: BackendTransmissionEdge[];
  availability: {
    evidence: Availability;
    opinions: Availability;
    transmission: Availability;
    impact: Availability;
    report: Availability;
  };
}): EventDetail {
  const { workspace, evidence, opinions, transmission, availability } = input;
  return {
    ...adaptEventSummary(workspace.event),
    timeline: adaptTimeline(workspace, opinions),
    opinions: adaptOpinions(opinions, evidence),
    graph: adaptTransmission(transmission),
    evidence: adaptEvidence(evidence),
    availability,
  };
}
