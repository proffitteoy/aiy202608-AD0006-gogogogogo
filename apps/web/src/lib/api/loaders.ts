import type {
  EventDetail,
  EventSummary,
  PlatformPulse,
  ResearchReport,
} from "@/lib/types";

import { adaptEventDetail, adaptEventSummary, adaptReportDetail } from "./adapters";
import { ApiError } from "./client";
import {
  fetchEventEvidence,
  fetchEventImpact,
  fetchEventList,
  fetchEventOpinions,
  fetchEventTransmission,
  fetchEventWorkspace,
} from "./events";
import { fetchReport } from "./reports";

export type ListLoadResult =
  | { status: "ready"; data: EventSummary[] }
  | { status: "degraded"; data: EventSummary[]; reason: string };

export type DetailLoadResult =
  | { status: "ready"; data: EventDetail; warnings: string[] }
  | { status: "not_found" }
  | { status: "unavailable"; reason: string };

export type ReportLoadResult =
  | { status: "ready"; data: ResearchReport }
  | { status: "not_found" }
  | { status: "unavailable"; reason: string };

function errorReason(error: unknown): string {
  if (error instanceof ApiError) {
    return error.status === 0 ? "后端不可达" : `后端返回 HTTP ${error.status}`;
  }
  return "后端请求失败";
}

export async function loadEventList(): Promise<ListLoadResult> {
  try {
    const list = await fetchEventList();
    return {
      status: "ready",
      data: list.items.map((raw) => adaptEventSummary(raw)),
    };
  } catch (error) {
    return { status: "degraded", data: [], reason: errorReason(error) };
  }
}

export function derivePulse(events: EventSummary[]): PlatformPulse {
  return {
    totalEvents: events.length,
    activeEvents: events.filter((event) =>
      ["active", "analyzed", "alerted"].includes(event.status.toLowerCase()),
    ).length,
    scoredEvents: events.filter(
      (event) => event.score.calibratedScore !== null,
    ).length,
    documentCount: events.reduce((sum, event) => sum + event.sourceCount, 0),
  };
}

export async function loadEventDetail(id: string): Promise<DetailLoadResult> {
  try {
    const workspace = await fetchEventWorkspace(id);
    const [evidenceResult, opinionsResult, transmissionResult, impactResult] =
      await Promise.allSettled([
        fetchEventEvidence(id),
        fetchEventOpinions(id),
        fetchEventTransmission(id),
        fetchEventImpact(id),
      ]);

    const evidence =
      evidenceResult.status === "fulfilled" ? evidenceResult.value.items : [];
    const opinions =
      opinionsResult.status === "fulfilled" ? opinionsResult.value.items : [];
    const transmission =
      transmissionResult.status === "fulfilled"
        ? transmissionResult.value.items
        : [];
    const impactMatrix =
      impactResult.status === "fulfilled" ? impactResult.value.items : [];

    const warnings: string[] = [];
    if (evidenceResult.status === "rejected") warnings.push("证据接口不可用");
    if (opinionsResult.status === "rejected") warnings.push("观点归因接口不可用");
    if (transmissionResult.status === "rejected") {
      warnings.push("传导假设接口不可用");
    }
    if (impactResult.status === "rejected") warnings.push("热力矩阵接口不可用");

    return {
      status: "ready",
      warnings,
      data: adaptEventDetail({
        workspace,
        evidence,
        opinions,
        transmission,
        impactMatrix,
        availability: {
          evidence:
            evidenceResult.status === "fulfilled" ? "available" : "degraded",
          opinions:
            opinionsResult.status === "rejected"
              ? "degraded"
              : opinions.length > 0
                ? "available"
                : "not_generated",
          transmission:
            transmissionResult.status === "rejected"
              ? "degraded"
              : transmission.length > 0
                ? "available"
                : "not_generated",
          impact:
            impactResult.status === "rejected"
              ? "degraded"
              : impactMatrix.length > 0
                ? "available"
                : "not_generated",
          report: "not_generated",
        },
      }),
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { status: "not_found" };
    }
    return { status: "unavailable", reason: errorReason(error) };
  }
}

export async function loadReportDetail(id: string): Promise<ReportLoadResult> {
  try {
    const report = await fetchReport(id);
    return {
      status: "ready",
      data: adaptReportDetail(report),
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { status: "not_found" };
    }
    return { status: "unavailable", reason: errorReason(error) };
  }
}
