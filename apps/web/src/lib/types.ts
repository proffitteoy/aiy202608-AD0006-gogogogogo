/** RiskTrace 前端展示契约。权威评分和分析结论只能来自后端。 */

export type Availability = "available" | "not_generated" | "degraded";
export type ScoreStatus = "complete" | "degraded" | "unavailable";

export interface DataFreshness {
  staleMinutes?: number;
  updatedAt: string;
}

export interface ScoreInterval {
  lowerBound: number;
  upperBound: number;
}

export interface EventScore {
  status: ScoreStatus;
  rawScore: number | null;
  calibratedScore: number | null;
  confidence: number | null;
  scoreInterval: ScoreInterval | null;
  scoringVersion: string | null;
  calibrationVersion: string | null;
  calculationId: string | null;
  scoreCalculationId: string | null;
  degradationReasons: string[];
}

export interface EventSummary {
  id: string;
  title: string;
  status: string;
  publishedAt: string;
  sourceCount: number;
  authoritativeSourceCount: number;
  sourceBreakdown: Record<string, number>;
  score: EventScore;
  freshness?: DataFreshness;
}

export interface EventDetail extends EventSummary {
  timeline: TimelinePoint[];
  opinions: OpinionAttribution[];
  graph: TransmissionGraph;
  impactMatrix: ImpactMatrixRow[];
  evidence: EvidenceItem[];
  availability: {
    evidence: Availability;
    opinions: Availability;
    transmission: Availability;
    impact: Availability;
    report: Availability;
  };
}

export interface TimelinePoint {
  id: string;
  timestamp: string;
  documentCount: number;
  sentiment: number | null;
  label?: string;
  evidenceIds: string[];
}

export interface OpinionAttribution {
  id: string;
  stance: string;
  emotion: string;
  reason: string;
  claimType: string;
  confidence: number;
  excerpt: string;
  source: string;
  publishedAt: string;
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
}

export interface TransmissionEdge {
  id: string;
  source: string;
  target: string;
  confidence: number;
  status: string;
  mechanism: string;
  direction: string;
  horizon: string;
  evidenceIds: string[];
}

export interface ImpactMatrixRow {
  entityId: string;
  entityName: string;
  entityType: string;
  direction: string;
  impactStrength: number;
  businessExposure: number;
  opinionSupport: number;
  factSupport: number;
  timeHorizon: string;
  compositeConfidence: number;
  edgeCount: number;
  opinionCount: number;
  evidenceCount: number;
  evidenceIds: string[];
}

export interface EvidenceItem {
  id: string;
  source: string;
  sourceTier: "authoritative" | "media" | "social" | "market";
  publishedAt: string;
  title: string;
  body: string;
  citedSpans: string[];
  linkUrl?: string;
  capturedAt: string;
  collectionMethod: string;
  licenseScope: string;
}

export interface PlatformPulse {
  totalEvents: number;
  activeEvents: number;
  scoredEvents: number;
  documentCount: number;
}

export interface ReportStatement {
  id: string;
  text: string;
  evidenceIds: string[];
  calculationIds: string[];
}

export interface ReportSection {
  id: string;
  title: string;
  status: string;
  items: ReportStatement[];
}

export interface ReportSnapshotSummary {
  id: string;
  eventId: string;
  snapshotAt: string;
  analysisVersion: string;
  scoreStatus: string;
  evidenceCount: number;
  sourceCount: number;
  scoringVersion: string | null;
  calibrationVersion: string | null;
}

export interface ReportEventSummary {
  id: string;
  title: string;
  status: string;
  publishedAt: string;
  sourceCount: number;
  authoritativeSourceCount: number;
  sourceBreakdown: Record<string, number>;
  score: EventScore;
}

export interface ResearchReport {
  id: string;
  eventId: string;
  snapshotId: string;
  format: string;
  status: string;
  title: string;
  summary: string;
  renderEngine: string;
  briefPromptVersion: string;
  bodyHtml: string;
  evidenceIds: string[];
  calculationIds: string[];
  degradationReasons: string[];
  createdAt: string;
  snapshot: ReportSnapshotSummary;
  event: ReportEventSummary;
  sections: ReportSection[];
  evidence: EvidenceItem[];
}
