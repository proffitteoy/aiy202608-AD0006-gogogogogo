"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import styles from "./ReportLaunchButton.module.css";

type Props = {
  eventId: string;
};

function normalizeReportError(message: string): string {
  if (message === "Not Found" || message.includes("HTTP 404")) {
    return "当前 API 进程未暴露报告接口，请确认后端已重启到包含 /api/reports 的版本。";
  }
  if (
    message.includes("fetch failed") ||
    message.includes("upstream_unreachable") ||
    message.includes("网络请求失败")
  ) {
    return "Web 代理当前无法连接后端 API，请检查 RISKTRACE_API_URL 和后端进程。";
  }
  return message;
}

function extractErrorMessage(payload: unknown, status: number): string {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }
  return `生成报告失败（HTTP ${status}）`;
}

export function ReportLaunchButton({ eventId }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/backend/reports", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ event_id: eventId, format: "html" }),
      });
      const payload = (await response.json().catch(() => null)) as
        | { id?: string; detail?: string }
        | null;

      if (!response.ok || !payload?.id) {
        throw new Error(extractErrorMessage(payload, response.status));
      }

      startTransition(() => {
        router.push(`/reports/${payload.id}`);
      });
    } catch (caughtError) {
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : "生成报告失败，请稍后重试。";
      setError(
        normalizeReportError(message),
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const disabled = isSubmitting || isPending;

  return (
    <div className={styles.action}>
      <button
        type="button"
        className={styles.button}
        onClick={handleClick}
        disabled={disabled}
        title="冻结当前 snapshot 并生成 HTML 风险简报"
      >
        {disabled ? "生成中…" : "生成报告"}
      </button>
      {error ? (
        <p className={styles.error} role="status">
          {error}
        </p>
      ) : null}
    </div>
  );
}
