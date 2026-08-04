import { NextResponse } from "next/server";

const apiBaseUrl = process.env.RISKTRACE_API_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  try {
    const response = await fetch(`${apiBaseUrl}/api/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    const body: unknown = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        status: "unavailable",
        service: "risktrace-api",
        detail: "无法连接后端。系统没有使用模拟状态替代真实依赖。",
      },
      { status: 503 },
    );
  }
}
