/**
 * 后端 API 客户端。
 *
 * - **服务端组件 / Route Handler** 直接调用 `apiFetch` → 走 RISKTRACE_API_URL（默认 127.0.0.1:8000）。
 * - **客户端组件** 建议走 `/api/backend/…` 反向代理，避免 CORS 与暴露内部地址。
 *
 * 统一抛 `ApiError`，业务层可以按 `error.status` 决定 fallback。
 */

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_TIMEOUT_MS = 2500;

export class ApiError extends Error {
  readonly status: number;
  readonly detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function getApiBaseUrl(): string {
  return process.env.RISKTRACE_API_URL?.trim() || DEFAULT_BASE_URL;
}

type ApiFetchInit = Omit<RequestInit, "body"> & {
  body?: unknown;
  timeoutMs?: number;
  /** Next 数据缓存 TTL（秒）；默认 30，写请求或 body 非空时会自动关闭 */
  revalidateSec?: number;
};

export async function apiFetch<T>(path: string, init: ApiFetchInit = {}): Promise<T> {
  const base = getApiBaseUrl();
  const url = new URL(path.startsWith("/") ? path : `/${path}`, base);
  const {
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    revalidateSec = 30,
    headers,
    method,
    ...rest
  } = init;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const isWrite = body !== undefined || (method && method.toUpperCase() !== "GET");
  const nextInit = isWrite
    ? { cache: "no-store" as const }
    : { next: { revalidate: revalidateSec } };

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      method,
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      ...nextInit,
    });
  } catch (err) {
    clearTimeout(timer);
    const detail = err instanceof Error ? err.message : String(err);
    throw new ApiError(`网络请求失败: ${detail}`, 0, detail);
  }
  clearTimeout(timer);

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text().catch(() => null);
    }
    throw new ApiError(
      `HTTP ${response.status} ${response.statusText}`,
      response.status,
      detail,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
