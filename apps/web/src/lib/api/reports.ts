import { apiFetch } from "./client";
import type { BackendReportDetail } from "./backend-types";

export async function fetchReport(id: string): Promise<BackendReportDetail> {
  return apiFetch<BackendReportDetail>(`/api/reports/${id}`);
}
