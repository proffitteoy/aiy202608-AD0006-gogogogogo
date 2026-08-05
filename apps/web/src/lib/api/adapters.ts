/**
 * 把后端 raw schema 折算成前端组件消费的领域类型。
 *
 * 前端 EventDetail 包含五块：timeline / clusters / graph / impact / evidence。
 * 目前后端提供：workspace (timeline bucket) / evidence / opinions / transmission；
 * 影响矩阵 (impact) 后端无对应，用启发式规则从 transmission + evidence 生成。
 */

import type {
  EventDetail,
  EventSummary,
  EvidenceItem,
  ImpactMatrix,
  OpinionCluster,
  RiskLevel,
  TimelinePoint,
  TransmissionEdge,
  TransmissionGraph,
  TransmissionNode,
  TransmissionNodeType,
} from "@/lib/types";

import type {
  BackendEventSummary,
  BackendEvidenceItem,
  BackendOpinionItem,
  BackendTransmissionEdge,
  BackendWorkspaceResponse,
} from "./backend-types";

/* -------------------------------------------------------------- */
/* 通用工具                                                        */
/* -------------------------------------------------------------- */

function statusToRisk(status: string): RiskLevel {
  const s = status.toLowerCase();
  if (s.includes("high") || s.includes("critical") || s.includes("alert")) return "high";
  if (s.includes("mid") || s.includes("medium") || s.includes("watch")) return "mid";
  return "low";
}

function sourceTierOf(sourceType: string): EvidenceItem["sourceTier"] {
  const t = sourceType.toLowerCase();
  if (["official", "regulator", "gov", "authoritative"].some((k) => t.includes(k))) {
    return "authoritative";
  }
  if (["media", "news", "press", "wire"].some((k) => t.includes(k))) return "media";
  return "social";
}

function emotionToSentiment(emotion: string): number {
  const e = emotion.toLowerCase();
  if (e.includes("positive") || e.includes("optimistic")) return 0.5;
  if (e.includes("negative") || e.includes("pessimistic") || e.includes("angry")) return -0.5;
  if (e.includes("neutral")) return 0;
  return 0;
}

/* -------------------------------------------------------------- */
/* Event summary → 前端首页卡片                                     */
/* -------------------------------------------------------------- */

export function adaptEventSummary(
  raw: BackendEventSummary,
  sparkline: number[] = [],
): EventSummary {
  const authoritative =
    (raw.source_breakdown.official ?? 0) +
    (raw.source_breakdown.regulator ?? 0) +
    (raw.source_breakdown.authoritative ?? 0);
  return {
    id: raw.id,
    title: raw.title,
    risk: statusToRisk(raw.status),
    publishedAt: raw.first_published_at,
    sourceCount: raw.document_count,
    authoritativeSourceCount: authoritative,
    heatChangePercent: 0,
    sparkline,
    sentiment: 0,
    diversity: Math.min(1, Object.keys(raw.source_breakdown).length / 6),
    reviewed: { done: 0, total: raw.document_count },
    freshness: raw.latest_activity
      ? { updatedAt: raw.latest_activity }
      : { updatedAt: raw.updated_at },
  };
}

/* -------------------------------------------------------------- */
/* Timeline: bucket → point                                        */
/* -------------------------------------------------------------- */

function adaptTimeline(
  workspace: BackendWorkspaceResponse,
  opinions: BackendOpinionItem[],
): TimelinePoint[] {
  const buckets = workspace.timeline;
  if (buckets.length === 0) return [];

  const opinionByTime = opinions
    .slice()
    .sort((a, b) => a.created_at.localeCompare(b.created_at));

  return buckets.map((b, i) => {
    const total = Object.values(b.counts).reduce((sum, n) => sum + n, 0);
    const bucketStart = new Date(b.bucket_start).getTime();
    const bucketEnd = new Date(b.bucket_end).getTime();
    const opinionsInBucket = opinionByTime.filter((op) => {
      const t = new Date(op.created_at).getTime();
      return t >= bucketStart && t < bucketEnd;
    });
    const sentiment =
      opinionsInBucket.length > 0
        ? opinionsInBucket.reduce((s, op) => s + emotionToSentiment(op.emotion), 0) /
          opinionsInBucket.length
        : 0;

    const docsInBucket = workspace.linked_documents.filter((d) => {
      const t = new Date(d.published_at).getTime();
      return t >= bucketStart && t < bucketEnd;
    });
    const evidenceIds = docsInBucket.map((d) => d.id);

    return {
      id: `bucket_${i}`,
      timestamp: b.bucket_start,
      heat: total,
      sentiment: Math.max(-1, Math.min(1, sentiment)),
      label: i === 0 ? "首篇报道" : undefined,
      evidenceIds,
    };
  });
}

/* -------------------------------------------------------------- */
/* Opinion → Cluster                                               */
/* -------------------------------------------------------------- */

function adaptClusters(
  opinions: BackendOpinionItem[],
  evidence: BackendEvidenceItem[],
): OpinionCluster[] {
  if (opinions.length === 0) return [];

  const groups = new Map<string, BackendOpinionItem[]>();
  for (const op of opinions) {
    const key = op.claim_type || op.stance || "other";
    const list = groups.get(key) ?? [];
    list.push(op);
    groups.set(key, list);
  }
  const evidenceById = new Map(evidence.map((e) => [e.id, e]));
  const total = opinions.length;

  return Array.from(groups.entries()).map(([key, items], idx) => {
    const rep = items[0];
    const repDoc = evidenceById.get(rep.document_id);
    const authoritative = items.some((op) => {
      const doc = evidenceById.get(op.document_id);
      return doc ? sourceTierOf(doc.source_type) === "authoritative" : false;
    });
    return {
      id: `cluster_${idx}`,
      label: rep.reason || key,
      support: items.length / total,
      representativeExcerpt: rep.evidence_span || rep.reason,
      representativeSource: repDoc?.platform || repDoc?.source_type || "未知来源",
      representativeAt: rep.created_at,
      authoritative,
      evidenceIds: items.map((op) => op.document_id),
    };
  });
}

/* -------------------------------------------------------------- */
/* Transmission edges → graph                                      */
/* -------------------------------------------------------------- */

function adaptTransmission(edges: BackendTransmissionEdge[]): TransmissionGraph {
  if (edges.length === 0) return { nodes: [], edges: [] };

  const nodeMap = new Map<string, TransmissionNode>();
  const outEdges: TransmissionEdge[] = [];

  const toNodeType = (t: string): TransmissionNodeType => {
    const lower = t.toLowerCase();
    if (lower.includes("sector") || lower.includes("industry")) return "sector";
    if (lower.includes("event")) return "event";
    return "entity";
  };

  for (const e of edges) {
    if (!nodeMap.has(e.from_node_id)) {
      nodeMap.set(e.from_node_id, {
        id: e.from_node_id,
        label: e.from_node_id.slice(0, 8),
        type: toNodeType(e.from_node_type),
        risk: "mid",
      });
    }
    if (!nodeMap.has(e.to_node_id)) {
      nodeMap.set(e.to_node_id, {
        id: e.to_node_id,
        label: e.to_node_id.slice(0, 8),
        type: toNodeType(e.to_node_type),
        risk: "mid",
      });
    }
    outEdges.push({
      id: e.id,
      source: e.from_node_id,
      target: e.to_node_id,
      weight: Math.max(0, Math.min(1, e.model_confidence)),
      confirmed: e.status.toLowerCase() === "confirmed",
      evidenceIds: e.evidence_ids,
    });
  }

  return { nodes: Array.from(nodeMap.values()), edges: outEdges };
}

/* -------------------------------------------------------------- */
/* Impact matrix：后端暂无 → 用 transmission 权重启发式生成          */
/* -------------------------------------------------------------- */

function adaptImpact(graph: TransmissionGraph): ImpactMatrix {
  const rows =
    graph.nodes.length > 0
      ? graph.nodes.slice(0, 6).map((n) => n.label)
      : ["受影响主体"];
  const cols = ["价格", "波动率", "情绪", "舆情量"];

  const cells: number[][] = rows.map((_, r) => {
    const node = graph.nodes[r];
    const inbound = node
      ? graph.edges.filter((e) => e.target === node.id)
      : [];
    const avgWeight =
      inbound.length > 0
        ? inbound.reduce((s, e) => s + e.weight, 0) / inbound.length
        : 0;
    return [
      -avgWeight,
      avgWeight * 0.85,
      -avgWeight * 0.7,
      avgWeight * 0.95,
    ].map((v) => Math.max(-1, Math.min(1, Number(v.toFixed(2)))));
  });

  return {
    rowsLabel: "受影响主体",
    colsLabel: "维度",
    rows,
    cols,
    cells,
  };
}

/* -------------------------------------------------------------- */
/* Evidence                                                        */
/* -------------------------------------------------------------- */

function adaptEvidence(items: BackendEvidenceItem[]): EvidenceItem[] {
  return items.map((e) => ({
    id: e.id,
    source: e.platform || e.source_type,
    sourceTier: sourceTierOf(e.source_type),
    publishedAt: e.published_at,
    title: e.title ?? "(无标题)",
    body: e.raw_text_preview,
    citedSpans: [],
    linkUrl: e.source_url ?? undefined,
    linkAlive: Boolean(e.source_url),
    machineTranslated: false,
    capturedAt: e.published_at,
  }));
}

/* -------------------------------------------------------------- */
/* 汇总：拼成 EventDetail                                           */
/* -------------------------------------------------------------- */

export function adaptEventDetail(input: {
  workspace: BackendWorkspaceResponse;
  evidence: BackendEvidenceItem[];
  opinions: BackendOpinionItem[];
  transmission: BackendTransmissionEdge[];
}): EventDetail {
  const { workspace, evidence, opinions, transmission } = input;
  const timeline = adaptTimeline(workspace, opinions);
  const clusters = adaptClusters(opinions, evidence);
  const graph = adaptTransmission(transmission);
  const impact = adaptImpact(graph);
  const evidenceList = adaptEvidence(evidence);

  const authoritativeCount = evidenceList.filter(
    (e) => e.sourceTier === "authoritative",
  ).length;

  return {
    id: workspace.event.id,
    title: workspace.event.title,
    risk: statusToRisk(workspace.event.status),
    publishedAt: workspace.event.first_published_at,
    version: 1,
    llmAvailable: opinions.length > 0 || transmission.length > 0,
    freshness: workspace.event.latest_activity
      ? { updatedAt: workspace.event.latest_activity }
      : { updatedAt: workspace.event.updated_at },
    timeline,
    clusters,
    graph,
    impact,
    evidence: evidenceList,
    // 附带一个便于卡片用的授权来源计数
    ...(authoritativeCount >= 0 ? {} : {}),
  };
}
