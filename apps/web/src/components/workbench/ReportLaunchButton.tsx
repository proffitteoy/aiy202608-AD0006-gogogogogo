"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  ReportGenerationOverlay,
  useReportPipeline,
} from "@/components/report/ReportGenerationOverlay";

import styles from "./ReportLaunchButton.module.css";

type Props = {
  eventId: string;
};

const AUTO_JUMP_MS = 900;

export function ReportLaunchButton({ eventId }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLDivElement | null>(null);
  const jumpedRef = useRef(false);

  const handleDone = useCallback(
    (reportId: string) => {
      if (jumpedRef.current) return;
      jumpedRef.current = true;
      window.setTimeout(() => {
        router.push(`/reports/${reportId}`);
      }, AUTO_JUMP_MS);
    },
    [router],
  );

  const pipeline = useReportPipeline(eventId, handleDone);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const start = useCallback(() => {
    if (pipeline.running) {
      setOpen(true);
      return;
    }
    jumpedRef.current = false;
    setOpen(true);
    void pipeline.start();
  }, [pipeline]);

  const label = pipeline.running
    ? "生成中…"
    : pipeline.hasRun && !pipeline.hadError
      ? "重新生成"
      : "生成报告";

  return (
    <div className={styles.action} ref={anchorRef}>
      <button
        type="button"
        className={styles.button}
        onClick={start}
        disabled={pipeline.running}
        title="冻结 snapshot 并让 AI 与模板协同撰写分段报告"
      >
        {label}
      </button>
      {pipeline.fatal ? (
        <p className={styles.error} role="status">
          {pipeline.fatal}
        </p>
      ) : null}
      {open ? (
        <ReportGenerationOverlay
          pipeline={pipeline}
          onClose={() => setOpen(false)}
          anchorRef={anchorRef}
        />
      ) : null}
    </div>
  );
}
