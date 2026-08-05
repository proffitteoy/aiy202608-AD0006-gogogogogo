/**
 * Server-side loader：屏蔽掉「后端可能挂 / 数据可能空」的细节，
 * 页面组件只关心一个稳定的 EventDetail/EventSummary[] 结果。
 */

import { ApiError, isMockFallbackAllowed } from "./client";
import { adaptEventDetail, adaptEventSummary } from "./adapters";
import {
  fetchEventEvidence,
  fetchEventList,
  fetchEventOpinions,
  fetchEventTransmission,
  fetchEventWorkspace,
} from "./events";
import type { EventDetail, EventSummary } from "@/lib/types";
import { eventDetail as mockEventDetail } from "@/lib/mock/event-detail";
import { events as mockEvents, pulse as mockPulse } from "@/lib/mock/events";
import type { PlatformPulse } from "@/lib/types";

export type LoadResult<T> =
  | { source: "backend"; data: T }
  | { source: "mock"; data: T; reason: string };

function fallback<T>(data: T, reason: string): LoadResult<T> {
  return { source: "mock", data, reason };
}

export async function loadEventList(): Promise<LoadResult<EventSummary[]>> {
  try {
    const list = await fetchEventList();
    if (list.items.length === 0) {
      if (isMockFallbackAllowed()) return fallback(mockEvents, "后端返回空列表");
      return { source: "backend", data: [] };
    }
    return {
      source: "backend",
      data: list.items.map((raw) => adaptEventSummary(raw)),
    };
  } catch (err) {
    if (!isMockFallbackAllowed()) throw err;
    const reason =
      err instanceof ApiError ? `${err.status} ${err.message}` : "后端不可达";
    return fallback(mockEvents, reason);
  }
}

export async function loadPulse(): Promise<LoadResult<PlatformPulse>> {
  // 后端暂无 pulse 端点，先透传 mock
  return fallback(mockPulse, "后端暂无平台指标端点");
}

export async function loadEventDetail(
  id: string,
): Promise<LoadResult<EventDetail> | null> {
  try {
    const [workspace, evidence, opinions, transmission] = await Promise.all([
      fetchEventWorkspace(id),
      fetchEventEvidence(id).catch(() => ({ items: [], total: 0 })),
      fetchEventOpinions(id).catch(() => ({ items: [], total: 0 })),
      fetchEventTransmission(id).catch(() => ({ items: [], total: 0 })),
    ]);

    return {
      source: "backend",
      data: adaptEventDetail({
        workspace,
        evidence: evidence.items,
        opinions: opinions.items,
        transmission: transmission.items,
      }),
    };
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      if (isMockFallbackAllowed() && id === mockEventDetail.id) {
        return fallback(mockEventDetail, "后端未找到该事件");
      }
      return null;
    }
    if (!isMockFallbackAllowed()) throw err;
    if (id !== mockEventDetail.id) return null;
    const reason =
      err instanceof ApiError ? `${err.status} ${err.message}` : "后端不可达";
    return fallback(mockEventDetail, reason);
  }
}
