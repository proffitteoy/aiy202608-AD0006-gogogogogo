/**
 * RiskTrace 前端领域类型。
 * 骨架阶段作为 mock 数据 + 组件 props 的 single source of truth；
 * 后续接后端时可与 openapi-typescript 生成产物合并。
 */

export type RiskLevel = "high" | "mid" | "low";

/** 数据源状态（用于 stale/degraded 标记） */
export interface DataFreshness {
  staleMinutes?: number;
  updatedAt: string; // ISO
}

/* ---------------------------------------------------------------
 * 首页：事件流卡片
 * ------------------------------------------------------------- */

export interface EventSummary {
  id: string;
  title: string;
  risk: RiskLevel;
  publishedAt: string; // ISO
  sourceCount: number;
  authoritativeSourceCount: number;
  /** 热度变化百分比，可正可负 */
  heatChangePercent: number;
  /** 24 小时热度采样（24 个点），用于 sparkline */
  sparkline: number[];
  /** 净情绪 [-1, 1] */
  sentiment: number;
  /** 来源多样性 [0, 1] */
  diversity: number;
  reviewed: { done: number; total: number };
  freshness?: DataFreshness;
}

/* ---------------------------------------------------------------
 * 工作台：单事件完整视图
 * ------------------------------------------------------------- */

export interface EventDetail {
  id: string;
  title: string;
  risk: RiskLevel;
  publishedAt: string;
  version: number;
  timeline: TimelinePoint[];
  clusters: OpinionCluster[];
  graph: TransmissionGraph;
  impact: ImpactMatrix;
  evidence: EvidenceItem[];
  llmAvailable: boolean;
  freshness?: DataFreshness;
}

export interface TimelinePoint {
  id: string;
  timestamp: string;
  heat: number;
  sentiment: number;
  /** AI 抽取的转折点标签 */
  label?: string;
  evidenceIds: string[];
}

export interface OpinionCluster {
  id: string;
  label: string;
  /** 支持度 [0, 1] */
  support: number;
  representativeExcerpt: string;
  representativeSource: string;
  representativeAt: string;
  authoritative: boolean;
  evidenceIds: string[];
}

export interface TransmissionGraph {
  nodes: TransmissionNode[];
  edges: TransmissionEdge[];
}

export type TransmissionNodeType = "entity" | "sector" | "event";

export interface TransmissionNode {
  id: string;
  label: string;
  type: TransmissionNodeType;
  risk: RiskLevel;
}

export interface TransmissionEdge {
  id: string;
  source: string;
  target: string;
  /** 权重 [0, 1] */
  weight: number;
  confirmed: boolean;
  evidenceIds: string[];
}

export interface ImpactMatrix {
  rowsLabel: string;
  colsLabel: string;
  rows: string[]; // 受影响主体
  cols: string[]; // 维度：价格、波动率、情绪、舆情量
  /** cells[rowIdx][colIdx] ∈ [-1, 1]，符号表示正负影响 */
  cells: number[][];
}

/* ---------------------------------------------------------------
 * 证据
 * ------------------------------------------------------------- */

export interface EvidenceItem {
  id: string;
  source: string;
  sourceTier: "authoritative" | "media" | "social";
  publishedAt: string;
  title: string;
  /** 完整正文（可能是快照） */
  body: string;
  /** AI 引用的句子片段（用于高亮） */
  citedSpans: string[];
  linkUrl?: string;
  /** 链接是否可访问 */
  linkAlive: boolean;
  /** 是否机器翻译 */
  machineTranslated: boolean;
  /** 快照采集时间 */
  capturedAt: string;
}

/* ---------------------------------------------------------------
 * 首页顶部指标
 * ------------------------------------------------------------- */

export interface PlatformPulse {
  activeEvents: number;
  highRiskEvents: number;
  pendingReview: number;
  /** 过去 24h 热度峰值曲线（用于 sparkline） */
  heatWave: number[];
}
