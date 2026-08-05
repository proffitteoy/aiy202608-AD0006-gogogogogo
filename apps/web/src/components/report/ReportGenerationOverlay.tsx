"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import styles from "@/components/workbench/AnalysisPipelinePanel.module.css";

type StageKey =
  | "freeze"
  | "overview"
  | "opinions"
  | "transmission"
  | "impact"
  | "recommendations"
  | "counter-evidence"
  | "risk-notes"
  | "persist";

type StageStatus = "pending" | "running" | "done" | "error";

type StageState = {
  status: StageStatus;
  label: string;
  note?: string;
  source?: "llm" | "template" | "template-fallback";
  startedAt?: number;
  finishedAt?: number;
};

type LogLine = {
  id: string;
  stage: StageKey;
  text: string;
  tone?: "info" | "warn" | "error" | "success";
};

type ReportEvent =
  | { type: "stage_start"; data: { stage: StageKey; label: string; uses_llm?: boolean } }
  | {
      type: "stage_progress";
      data: { stage: StageKey; warning?: string; error?: string };
    }
  | {
      type: "stage_done";
      data: {
        stage: StageKey;
        elapsed_ms: number;
        source?: "llm" | "template" | "template-fallback";
        statements?: number;
        report_id?: string;
        status?: string;
        error?: string;
        snapshot_id?: string;
      };
    }
  | { type: "stage_error"; data: { stage: StageKey; error: string } }
  | { type: "llm_start"; data: { section: StageKey; model: string } }
  | { type: "llm_delta"; data: { section: StageKey; delta: string } }
  | { type: "llm_done"; data: { section: StageKey; bytes: number } }
  | {
      type: "done";
      data: {
        report_id: string;
        status: string;
        elapsed_ms: number;
        degradation_reasons: string[];
      };
    }
  | { type: "fatal"; data: { error: string } };

const STAGES: readonly StageKey[] = [
  "freeze",
  "overview",
  "opinions",
  "transmission",
  "impact",
  "recommendations",
  "counter-evidence",
  "risk-notes",
  "persist",
];

const DEFAULT_STAGE_LABELS: Record<StageKey, string> = {
  freeze: "冻结分析快照",
  overview: "AI 撰写事件摘要",
  opinions: "整理市场观点",
  transmission: "梳理传导路径",
  impact: "汇总影响对象",
  recommendations: "AI 生成研究建议",
  "counter-evidence": "整理反向证据",
  "risk-notes": "AI 撰写风险提示",
  persist: "写入报告存档",
};

const STAGE_ICONS: Record<StageKey, string> = {
  freeze: "❄",
  overview: "✎",
  opinions: "❝",
  transmission: "⇋",
  impact: "▦",
  recommendations: "★",
  "counter-evidence": "⇌",
  "risk-notes": "△",
  persist: "▤",
};

const LLM_STAGES = new Set<StageKey>(["overview", "recommendations", "risk-notes"]);
const MAX_LOG_LINES = 60;

function initialStages(): Record<StageKey, StageState> {
  return STAGES.reduce(
    (acc, stage) => {
      acc[stage] = { status: "pending", label: DEFAULT_STAGE_LABELS[stage] };
      return acc;
    },
    {} as Record<StageKey, StageState>,
  );
}

type ReportPipelineState = {
  running: boolean;
  stages: Record<StageKey, StageState>;
  logs: LogLine[];
  llmStream: { stage: StageKey | null; text: string };
  elapsedMs: number | null;
  fatal: string | null;
  hasRun: boolean;
  hadError: boolean;
  reportId: string | null;
  start: () => Promise<void>;
};

function useReportPipeline(
  eventId: string,
  onDone: (reportId: string) => void,
): ReportPipelineState {
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<Record<StageKey, StageState>>(initialStages());
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [llmStream, setLlmStream] = useState<{ stage: StageKey | null; text: string }>({
    stage: null,
    text: "",
  });
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState(false);
  const [hadError, setHadError] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const logCounterRef = useRef(0);

  const appendLog = useCallback(
    (entry: Omit<LogLine, "id">) => {
      setLogs((prev) => {
        const id = `${Date.now()}-${logCounterRef.current++}`;
        const next = [...prev, { ...entry, id }];
        return next.slice(-MAX_LOG_LINES);
      });
    },
    [],
  );

  const handleEvent = useCallback(
    (evt: ReportEvent) => {
      switch (evt.type) {
        case "stage_start": {
          const stage = evt.data.stage;
          setStages((prev) => ({
            ...prev,
            [stage]: {
              ...prev[stage],
              status: "running",
              label: evt.data.label || prev[stage].label,
              startedAt: performance.now(),
            },
          }));
          appendLog({
            stage,
            text: `▶ ${evt.data.label || DEFAULT_STAGE_LABELS[stage]}${LLM_STAGES.has(stage) ? "（AI）" : ""}`,
            tone: "info",
          });
          break;
        }
        case "stage_progress": {
          if (evt.data.warning) {
            appendLog({
              stage: evt.data.stage,
              text: `⚠ ${evt.data.warning}${evt.data.error ? `（${evt.data.error}）` : ""}`,
              tone: "warn",
            });
          }
          break;
        }
        case "stage_done": {
          const stage = evt.data.stage;
          const src = evt.data.source;
          setStages((prev) => ({
            ...prev,
            [stage]: {
              ...prev[stage],
              status: "done",
              source: src,
              finishedAt: performance.now(),
              note:
                src === "template-fallback"
                  ? "AI 生成失败，已回退模板"
                  : src === "llm"
                    ? `AI 产出 ${evt.data.statements ?? 0} 条`
                    : src === "template"
                      ? `模板 · ${evt.data.statements ?? 0} 条`
                      : undefined,
            },
          }));
          appendLog({
            stage,
            text:
              src === "template-fallback"
                ? `↩ 已回退模板 (${evt.data.elapsed_ms}ms)`
                : `✓ 完成 · ${src === "llm" ? "AI" : src === "template" ? "模板" : "内部"} · ${evt.data.elapsed_ms}ms`,
            tone: src === "template-fallback" ? "warn" : "success",
          });
          if (stage === "persist" && evt.data.report_id) {
            setReportId(evt.data.report_id);
          }
          break;
        }
        case "stage_error": {
          const stage = evt.data.stage;
          setStages((prev) => ({
            ...prev,
            [stage]: {
              ...prev[stage],
              status: "error",
              finishedAt: performance.now(),
              note: evt.data.error,
            },
          }));
          setHadError(true);
          appendLog({
            stage,
            text: `✗ ${evt.data.error}`,
            tone: "error",
          });
          break;
        }
        case "llm_start": {
          setLlmStream({ stage: evt.data.section, text: "" });
          appendLog({
            stage: evt.data.section,
            text: `⌁ 调用 ${evt.data.model}…`,
            tone: "info",
          });
          break;
        }
        case "llm_delta": {
          setLlmStream((prev) => ({
            stage: evt.data.section,
            text: (prev.stage === evt.data.section ? prev.text : "") + evt.data.delta,
          }));
          break;
        }
        case "llm_done": {
          appendLog({
            stage: evt.data.section,
            text: `⌁ AI 完成 · ${evt.data.bytes} 字节`,
            tone: "info",
          });
          break;
        }
        case "done": {
          setElapsedMs(evt.data.elapsed_ms);
          setReportId(evt.data.report_id);
          appendLog({
            stage: "persist",
            text: `✓ 报告已生成 · 用时 ${(evt.data.elapsed_ms / 1000).toFixed(1)}s`,
            tone: "success",
          });
          onDone(evt.data.report_id);
          break;
        }
        case "fatal": {
          setFatal(evt.data.error);
          setHadError(true);
          appendLog({
            stage: "persist",
            text: `‼ 致命错误: ${evt.data.error}`,
            tone: "error",
          });
          break;
        }
      }
    },
    [appendLog, onDone],
  );

  const start = useCallback(async () => {
    if (running) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRunning(true);
    setHasRun(true);
    setHadError(false);
    setStages(initialStages());
    setLogs([]);
    setLlmStream({ stage: null, text: "" });
    setElapsedMs(null);
    setFatal(null);
    setReportId(null);

    try {
      const res = await fetch("/api/backend/reports/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ event_id: eventId, format: "html" }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        const detail = await res.text().catch(() => "");
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut = buffer.indexOf("\n\n");
        while (cut >= 0) {
          const frame = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);
          cut = buffer.indexOf("\n\n");
          if (!frame.trim() || frame.startsWith(":")) continue;
          let eventName = "message";
          const dataLines: string[] = [];
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) eventName = line.slice(6).trim();
            else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
          }
          if (!dataLines.length) continue;
          try {
            const payload = JSON.parse(dataLines.join("\n"));
            handleEvent({ type: eventName, data: payload } as ReportEvent);
          } catch (err) {
            console.warn("Report SSE parse error", err, frame);
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const message = (err as Error).message || String(err);
      setFatal(message);
      setHadError(true);
      setStages((prev) => {
        const next = { ...prev };
        for (const key of STAGES) {
          const cur = next[key];
          if (cur.status === "pending" || cur.status === "running") {
            next[key] = {
              ...cur,
              status: "error",
              note: cur.status === "running" ? message : "未启动（上游错误）",
              finishedAt: performance.now(),
            };
          }
        }
        return next;
      });
      appendLog({
        stage: "persist",
        text: `‼ 连接错误: ${message}`,
        tone: "error",
      });
    } finally {
      setRunning(false);
    }
  }, [eventId, handleEvent, running, appendLog]);

  useEffect(() => () => abortRef.current?.abort(), []);

  return {
    running,
    stages,
    logs,
    llmStream,
    elapsedMs,
    fatal,
    hasRun,
    hadError,
    reportId,
    start,
  };
}

type OverlayProps = {
  pipeline: ReportPipelineState;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
};

export function ReportGenerationOverlay({ pipeline, onClose, anchorRef }: OverlayProps) {
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const compute = () => {
      const rect = anchorRef.current?.getBoundingClientRect();
      if (!rect) return;
      setPos({
        top: rect.bottom + 8,
        right: Math.max(16, window.innerWidth - rect.right),
      });
    };
    compute();
    window.addEventListener("resize", compute);
    window.addEventListener("scroll", compute, true);
    return () => {
      window.removeEventListener("resize", compute);
      window.removeEventListener("scroll", compute, true);
    };
  }, [anchorRef]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [pipeline.logs]);

  if (!pos) return null;

  const { stages, logs, llmStream, elapsedMs, fatal, running } = pipeline;

  return (
    <>
      <div className={styles.backdrop} onClick={onClose} aria-hidden="true" />
      <section
        className={styles.overlay}
        role="dialog"
        aria-label="报告生成流水线"
        style={{ top: pos.top, right: pos.right }}
      >
        <header className={styles.overlayHead}>
          <div className={styles.overlayTitle}>
            <span className={styles.overlayTitleIcon} aria-hidden="true">✎</span>
            <div>
              <div className={styles.overlayTitleText}>报告生成流水线</div>
              <div className={styles.overlayTitleSub}>
                {running
                  ? "AI 与模板协同生成中…"
                  : elapsedMs != null
                    ? `已完成 · 用时 ${(elapsedMs / 1000).toFixed(1)}s，即将跳转`
                    : "开始生成后可在此看到分段进度"}
              </div>
            </div>
          </div>
          <button
            type="button"
            className={styles.overlayClose}
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
        </header>

        <ol className={styles.timeline}>
          {STAGES.map((stage) => {
            const s = stages[stage];
            const isLlm = LLM_STAGES.has(stage);
            return (
              <li key={stage} className={styles.stage} data-status={s.status}>
                <span className={styles.stageIcon} aria-hidden="true">
                  {STAGE_ICONS[stage]}
                </span>
                <div className={styles.stageBody}>
                  <div className={styles.stageHead}>
                    <span className={styles.stageLabel}>
                      {s.label}
                      {isLlm ? (
                        <span
                          style={{
                            marginLeft: 6,
                            padding: "0 6px",
                            borderRadius: 4,
                            fontSize: 10,
                            letterSpacing: "0.04em",
                            background: "rgba(120, 200, 255, 0.12)",
                            color: "#7dd3fc",
                          }}
                        >
                          AI
                        </span>
                      ) : null}
                    </span>
                    <span className={styles.stageStatus} data-status={s.status}>
                      {s.status === "pending"
                        ? "待运行"
                        : s.status === "running"
                          ? "进行中"
                          : s.status === "done"
                            ? s.source === "template-fallback"
                              ? "已降级"
                              : "已完成"
                            : "错误"}
                    </span>
                  </div>
                  {s.note ? <div className={styles.stageNote}>{s.note}</div> : null}
                </div>
              </li>
            );
          })}
        </ol>

        {llmStream.stage && llmStream.text ? (
          <div className={styles.llmStream}>
            <div className={styles.llmStreamHead}>AI · {DEFAULT_STAGE_LABELS[llmStream.stage]}</div>
            <pre className={styles.llmStreamBody}>{llmStream.text.slice(-800)}</pre>
          </div>
        ) : null}

        <div ref={scrollRef} className={styles.console}>
          {logs.map((line) => (
            <div key={line.id} className={styles.logLine} data-tone={line.tone ?? "info"}>
              <span className={styles.logStage}>[{line.stage}]</span>
              <span className={styles.logText}>{line.text}</span>
            </div>
          ))}
          {fatal ? (
            <div className={styles.logLine} data-tone="error">
              <span className={styles.logStage}>[fatal]</span>
              <span className={styles.logText}>{fatal}</span>
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
}

export { useReportPipeline };
