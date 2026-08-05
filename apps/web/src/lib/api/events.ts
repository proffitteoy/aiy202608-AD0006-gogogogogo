/**
 * 后端 event 领域接口调用。仅在 Server Component 或 Route Handler 里直接使用。
 * 客户端组件如需请求应走 /api/backend/... 代理。
 */

import { apiFetch } from "./client";
import type {
  BackendEventSummary,
  BackendEvidenceItem,
  BackendImpactMatrixRow,
  BackendOpinionItem,
  BackendTransmissionEdge,
  BackendWorkspaceResponse,
  PaginatedResponse,
} from "./backend-types";

export async function fetchEventList(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<BackendEventSummary>> {
  return apiFetch<PaginatedResponse<BackendEventSummary>>(
    `/api/events?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchEventSummary(id: string): Promise<BackendEventSummary> {
  return apiFetch<BackendEventSummary>(`/api/events/${id}`);
}

export async function fetchEventWorkspace(id: string): Promise<BackendWorkspaceResponse> {
  return apiFetch<BackendWorkspaceResponse>(`/api/events/${id}/workspace`);
}

export async function fetchEventEvidence(
  id: string,
  page = 1,
  pageSize = 100,
): Promise<PaginatedResponse<BackendEvidenceItem>> {
  return apiFetch<PaginatedResponse<BackendEvidenceItem>>(
    `/api/events/${id}/evidence?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchEventOpinions(id: string): Promise<{
  items: BackendOpinionItem[];
  total: number;
}> {
  return apiFetch<{ items: BackendOpinionItem[]; total: number }>(
    `/api/events/${id}/opinions`,
  );
}

export async function fetchEventTransmission(id: string): Promise<{
  items: BackendTransmissionEdge[];
  total: number;
}> {
  return apiFetch<{ items: BackendTransmissionEdge[]; total: number }>(
    `/api/events/${id}/transmission`,
    { revalidateSec: 0 },
  );
}

export async function fetchEventImpact(id: string): Promise<{
  items: BackendImpactMatrixRow[];
  total: number;
}> {
  return apiFetch<{ items: BackendImpactMatrixRow[]; total: number }>(
    `/api/events/${id}/impact`,
    { revalidateSec: 0 },
  );
}
