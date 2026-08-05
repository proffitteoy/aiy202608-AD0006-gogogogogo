import { NextRequest, NextResponse } from "next/server";

import { getApiBaseUrl } from "@/lib/api/client";

/**
 * 反向代理 /api/backend/<path> → RISKTRACE_API_URL/api/<path>
 *
 * 用途：客户端组件只跟自身同源交互，避免 CORS，同时不把后端地址暴露到浏览器。
 */

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function forward(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = new URL(
    `/api/${path.join("/")}`,
    getApiBaseUrl(),
  );
  target.search = request.nextUrl.search;

  const forwardedHeaders = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (["host", "connection", "content-length"].includes(lower)) return;
    forwardedHeaders.set(key, value);
  });

  const method = request.method.toUpperCase() as Method;
  const init: RequestInit = {
    method,
    headers: forwardedHeaders,
    cache: "no-store",
  };
  if (method !== "GET" && method !== "DELETE") {
    const body = await request.text();
    if (body.length > 0) {
      init.body = body;
    }
  }

  try {
    const upstream = await fetch(target, init);
    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
      if (key.toLowerCase() === "content-encoding") return;
      responseHeaders.set(key, value);
    });
    const buf = await upstream.arrayBuffer();
    return new NextResponse(buf, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { status: "upstream_unreachable", detail },
      { status: 502 },
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
