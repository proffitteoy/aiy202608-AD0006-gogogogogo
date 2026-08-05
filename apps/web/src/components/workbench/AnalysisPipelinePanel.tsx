"use client";

import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import { useDemoReveal } from "./DemoRevealContext";
import styles from "./AnalysisPipelinePanel.module.css";

type StageKey =
  | "ingest"
  | "entities"
  | "opinions"
  | "transmission"
  | "impact"
  | "scoring";

type StageStatus = "pending" | "running" | "done" | "skipped" | "error";

type LogLine = {
  id: string;
  stage: StageKey;
  text: string;
  tone?: "info" | "item" | "warn" | "error" | "success";
};

type StageState = {
  status: StageStatus;
  label: string;
  produced?: number;
  note?: string;
  progress?: { current: number; total: number } | null;
  startedAt?: number;
  finishedAt?: number;
};

type PipelineEvent =
  | { type: "pipeline_start"; data: { event_id: string; event_title: string; stages: StageKey[] } }
  | {
      type: "stage_start";
      data: { stage: StageKey; label: string; total?: number; title?: string };
    }
  | {
      type: "stage_progress";
      data: {
        stage: StageKey;
        current?: number;
        total?: number;
        message?: string;
      };
    }
  | {
      type: "item";
      data: { stage: StageKey; payload: Record<string, unknown> };
    }
  | {
      type: "stage_done";
      data: {
        stage: StageKey;
        produced: number;
        skipped: boolean;
        note?: string | null;
      };
    }
  | { type: "stage_error"; data: { stage: StageKey; error: string } }
  | {
      type: "llm_delta";
      data: { stage: StageKey; delta: string; total_chars?: number };
    }
  | { type: "done"; data: { elapsed_ms: number; summary: Record<string, unknown> } }
  | { type: "fatal"; data: { error: string } };

const STAGES: readonly StageKey[] = [
  "ingest",
  "entities",
  "opinions",
  "transmission",
  "impact",
  "scoring",
] as const;

const DEFAULT_STAGE_LABELS: Record<StageKey, string> = {
  ingest: "读取事件证据",
  entities: "识别涉事主体",
  opinions: "归因观点抽取",
  transmission: "构造传导假设",
  impact: "计算影响矩阵",
  scoring: "评分校准与置信区间",
};

const STAGE_ICONS: Record<StageKey, string> = {
  ingest: "◔",
  entities: "◈",
  opinions: "❝",
  transmission: "⇋",
  impact: "▦",
  scoring: "⚖",
};

const MAX_LOG_LINES = 60;
const AUTO_CLOSE_MS = 2600;

function initialStages(): Record<StageKey, StageState> {
  return STAGES.reduce(
    (acc, stage) => {
      acc[stage] = { status: "pending", label: DEFAULT_STAGE_LABELS[stage] };
      return acc;
    },
    {} as Record<StageKey, StageState>,
  );
}

function summarizeItem(stage: StageKey, payload: Record<string, unknown>): string {
  switch (stage) {
    case "ingest":
      return `${payload.title ?? "?"} · ${payload.source ?? ""} · ${payload.platform ?? ""}`;
    case "entities":
      return `${payload.name ?? "未命名主体"} · ${payload.type ?? "unknown"}`;
    case "opinions":
      return `${payload.stance ?? "?"} · ${(payload.summary as string) || "（无摘要）"}`;
    case "transmission": {
      if (payload.kind === "doc") {
        return `[doc] ${payload.title ?? ""}`;
      }
      const conf = typeof payload.confidence === "number" ? payload.confidence : 0;
      const dir = String(payload.direction ?? "");
      return `[edge ${dir}] conf=${conf.toFixed(2)} · ${payload.mechanism ?? ""}`;
    }
    case "impact": {
      const score = typeof payload.score === "number" ? payload.score : 0;
      return `${payload.name ?? "?"} · ${payload.direction ?? "?"} · ${score.toFixed(2)}`;
    }
    case "scoring": {
      const raw = typeof payload.raw_score === "number" ? payload.raw_score : 0;
      const calibrated =
        typeof payload.calibrated_score === "number" ? payload.calibrated_score : 0;
      const confidence = typeof payload.confidence === "number" ? payload.confidence : 0;
      const lower = typeof payload.lower === "number" ? payload.lower : 0;
      const upper = typeof payload.upper === "number" ? payload.upper : 0;
      const reasons = Array.isArray(payload.degradation_reasons)
        ? payload.degradation_reasons.filter((v): v is string => typeof v === "string")
        : [];
      const suffix = reasons.length ? ` · 降级: ${reasons.join(",")}` : "";
      return (
        `raw=${raw.toFixed(2)} · calibrated=${calibrated.toFixed(2)} · ` +
        `conf=${confidence.toFixed(2)} · [${lower.toFixed(2)}-${upper.toFixed(2)}]${suffix}`
      );
    }
    default:
      return JSON.stringify(payload).slice(0, 120);
  }
}

type PipelineState = {
  running: boolean;
  stages: Record<StageKey, StageState>;
  logs: LogLine[];
  llmStream: { stage: StageKey | null; text: string };
  elapsedMs: number | null;
  fatal: string | null;
  hasRun: boolean;
  hadError: boolean;
  lastMode: "cache" | "fresh" | null;
  start: (opts?: { force?: boolean }) => Promise<void>;
};

function usePipeline(eventId: string, onDone: () => void): PipelineState {
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<Record<StageKey, StageState>>(initialStages);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [llmStream, setLlmStream] = useState<{ stage: StageKey | null; text: string }>({
    stage: null,
    text: "",
  });
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState(false);
  const [hadError, setHadError] = useState(false);
  const [lastMode, setLastMode] = useState<"cache" | "fresh" | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const logIdRef = useRef(0);

  const appendLog = useCallback((line: Omit<LogLine, "id">) => {
    logIdRef.current += 1;
    setLogs((prev) => {
      const next = [...prev, { id: `log-${logIdRef.current}`, ...line }];
      return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
    });
  }, []);

  const handleEvent = useCallback(
    (evt: PipelineEvent) => {
      switch (evt.type) {
        case "pipeline_start":
          appendLog({
            stage: "ingest",
            text: `▶ 分析开始 · ${evt.data.event_title}`,
            tone: "info",
          });
          break;
        case "stage_start":
          setStages((prev) => ({
            ...prev,
            [evt.data.stage]: {
              ...prev[evt.data.stage],
              status: "running",
              label: evt.data.label || prev[evt.data.stage].label,
              startedAt: performance.now(),
              progress: evt.data.total ? { current: 0, total: evt.data.total } : null,
            },
          }));
          appendLog({ stage: evt.data.stage, text: `→ ${evt.data.label}`, tone: "info" });
          break;
        case "stage_progress":
          setStages((prev) => {
            const current = prev[evt.data.stage];
            if (!current) return prev;
            const nextProgress =
              evt.data.current != null && evt.data.total != null
                ? { current: evt.data.current, total: evt.data.total }
                : current.progress ?? null;
            return {
              ...prev,
              [evt.data.stage]: { ...current, progress: nextProgress },
            };
          });
          if (evt.data.message) {
            appendLog({
              stage: evt.data.stage,
              text: `  · ${evt.data.message}`,
              tone: "info",
            });
          }
          break;
        case "item":
          appendLog({
            stage: evt.data.stage,
            text: `+ ${summarizeItem(evt.data.stage, evt.data.payload)}`,
            tone: "item",
          });
          break;
        case "stage_done":
          setStages((prev) => ({
            ...prev,
            [evt.data.stage]: {
              ...prev[evt.data.stage],
              status: evt.data.skipped ? "skipped" : "done",
              produced: evt.data.produced,
              note: evt.data.note ?? undefined,
              finishedAt: performance.now(),
              progress: null,
            },
          }));
          appendLog({
            stage: evt.data.stage,
            text: evt.data.skipped
              ? `↷ 跳过 (${evt.data.note ?? "无产出"})`
              : `✓ 完成 · 产出 ${evt.data.produced}`,
            tone: evt.data.skipped ? "warn" : "success",
          });
          break;
        case "stage_error":
          setStages((prev) => ({
            ...prev,
            [evt.data.stage]: {
              ...prev[evt.data.stage],
              status: "error",
              note: evt.data.error,
              finishedAt: performance.now(),
            },
          }));
          setHadError(true);
          appendLog({ stage: evt.data.stage, text: `✗ ${evt.data.error}`, tone: "error" });
          break;
        case "llm_delta":
          setLlmStream((prev) => {
            const same = prev.stage === evt.data.stage;
            return {
              stage: evt.data.stage,
              text: (same ? prev.text : "") + evt.data.delta,
            };
          });
          break;
        case "done":
          setElapsedMs(evt.data.elapsed_ms);
          appendLog({
            stage: "scoring",
            text: `● 分析完成 · ${(evt.data.elapsed_ms / 1000).toFixed(1)}s`,
            tone: "success",
          });
          onDone();
          break;
        case "fatal":
          setFatal(evt.data.error);
          setHadError(true);
          appendLog({
            stage: "scoring",
            text: `‼ 致命错误: ${evt.data.error}`,
            tone: "error",
          });
          break;
      }
    },
    [appendLog, onDone],
  );

  const start = useCallback(async (opts?: { force?: boolean }) => {
    if (running) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const forceRun = opts?.force ?? false;
    setLastMode(forceRun ? "fresh" : "cache");
    setRunning(true);
    setHasRun(true);
    setHadError(false);
    setStages(initialStages());
    setLogs([]);
    setLlmStream({ stage: null, text: "" });
    setElapsedMs(null);
    setFatal(null);

    try {
      const url = `/api/backend/events/${encodeURIComponent(eventId)}/analyze/stream${
        forceRun ? "?force=true" : ""
      }`;
      const res = await fetch(url, {
        method: "POST",
        headers: { Accept: "text/event-stream" },
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
            handleEvent({ type: eventName, data: payload } as PipelineEvent);
          } catch (err) {
            console.warn("SSE parse error", err, frame);
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      const message = (err as Error).message || String(err);
      setFatal(message);
      setHadError(true);
      // Bail every stage still marked pending/running so the UI stops "spinning".
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
              progress: null,
            };
          }
        }
        return next;
      });
      appendLog({
        stage: "scoring",
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
    lastMode,
    start,
  };
}

type Props = {
  eventId: string;
};

export function AnalysisPipelineTrigger({ eventId }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const anchorRef = useRef<HTMLDivElement | null>(null);

  const { reveal } = useDemoReveal();
  const pipeline = usePipeline(eventId, () => {
    reveal();
    router.refresh();
  });

  // Open overlay whenever a run starts; keep open on error until user dismisses.
  useEffect(() => {
    if (pipeline.running) setOpen(true);
  }, [pipeline.running]);

  useEffect(() => {
    if (pipeline.hadError) setOpen(true);
  }, [pipeline.hadError]);

  // Auto-close after successful completion.
  useEffect(() => {
    if (pipeline.running) return;
    if (!pipeline.hasRun) return;
    if (pipeline.hadError) return;
    if (pipeline.elapsedMs == null) return;
    const timer = window.setTimeout(() => setOpen(false), AUTO_CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [pipeline.running, pipeline.hasRun, pipeline.hadError, pipeline.elapsedMs]);

  // Esc closes overlay.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const runPrimary = useCallback(() => {
    if (pipeline.running) {
      setOpen((v) => !v);
      return;
    }
    setMenuOpen(false);
    setOpen(true);
    void pipeline.start({ force: false });
  }, [pipeline]);

  const runFresh = useCallback(() => {
    if (pipeline.running) return;
    setMenuOpen(false);
    setOpen(true);
    void pipeline.start({ force: true });
  }, [pipeline]);

  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (anchorRef.current && !anchorRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

  const primaryLabel = pipeline.running
    ? "分析中…"
    : pipeline.hasRun
      ? "快速回放"
      : "运行分析";

  return (
    <div className={styles.triggerWrap} ref={anchorRef}>
      <div className={styles.triggerSplit} data-running={pipeline.running}>
        <button
          type="button"
          className={styles.triggerBtn}
          onClick={runPrimary}
          data-running={pipeline.running}
          aria-expanded={open}
          aria-haspopup="dialog"
        >
          <span className={styles.triggerPips} aria-hidden="true">
            {STAGES.map((stage) => (
              <span
                key={stage}
                className={styles.pip}
                data-status={pipeline.stages[stage].status}
              />
            ))}
          </span>
          <span className={styles.triggerLabel}>{primaryLabel}</span>
          {pipeline.elapsedMs != null ? (
            <span className={styles.triggerElapsed} data-numeric>
              {(pipeline.elapsedMs / 1000).toFixed(1)}s
            </span>
          ) : null}
        </button>
        <button
          type="button"
          className={styles.triggerChevron}
          onClick={() => setMenuOpen((v) => !v)}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          aria-label="更多分析选项"
          disabled={pipeline.running}
        >
          ▾
        </button>
      </div>

      {menuOpen ? (
        <div className={styles.triggerMenu} role="menu">
          <button
            type="button"
            className={styles.menuItem}
            onClick={runPrimary}
            role="menuitem"
          >
            <div className={styles.menuItemTitle}>快速回放</div>
            <div className={styles.menuItemDesc}>
              读取上次结果 · 秒级返回 · 不消耗 LLM
            </div>
          </button>
          <button
            type="button"
            className={styles.menuItem}
            onClick={runFresh}
            role="menuitem"
          >
            <div className={styles.menuItemTitle}>重新分析</div>
            <div className={styles.menuItemDesc}>
              清除既有传导边 · 重新调用 LLM · 生成新的假设
            </div>
          </button>
        </div>
      ) : null}

      {pipeline.hasRun && !open && !pipeline.running ? (
        <button
          type="button"
          className={styles.triggerReveal}
          onClick={() => setOpen(true)}
          aria-label="展开分析详情"
        >
          详情 ▾
        </button>
      ) : null}

      {open ? (
        <AnalysisPipelineOverlay
          pipeline={pipeline}
          onClose={() => setOpen(false)}
          anchorRef={anchorRef}
        />
      ) : null}
    </div>
  );
}

type OverlayProps = {
  pipeline: PipelineState;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
};

function AnalysisPipelineOverlay({ pipeline, onClose, anchorRef }: OverlayProps) {
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
        aria-label="分析流水线"
        style={{ top: pos.top, right: pos.right }}
      >
        <header className={styles.overlayHead}>
          <div className={styles.overlayTitle}>
            <span className={styles.overlayTitleIcon} aria-hidden="true">⌁</span>
            <div>
              <div className={styles.overlayTitleText}>分析流水线</div>
              <div className={styles.overlayTitleSub}>
                {running
                  ? `正在运行 · ${pipeline.lastMode === "fresh" ? "重新分析（调 LLM）" : "快速回放（读缓存）"}`
                  : elapsedMs != null
                    ? `上次 ${pipeline.lastMode === "fresh" ? "重新分析" : "快速回放"} · ${(elapsedMs / 1000).toFixed(1)}s`
                    : "点击右上角的按钮开始分析"}
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
            return (
              <li key={stage} className={styles.stage} data-status={s.status}>
                <span className={styles.stageIcon} aria-hidden="true">
                  {STAGE_ICONS[stage]}
                </span>
                <div className={styles.stageBody}>
                  <div className={styles.stageHead}>
                    <span className={styles.stageLabel}>{s.label}</span>
                    <span className={styles.stageStatus} data-status={s.status}>
                      {s.status === "pending"
                        ? "待运行"
                        : s.status === "running"
                          ? "进行中"
                          : s.status === "done"
                            ? `产出 ${s.produced ?? 0}`
                            : s.status === "skipped"
                              ? "已跳过"
                              : "错误"}
                    </span>
                  </div>
                  {s.progress ? (
                    <div className={styles.progress}>
                      <span
                        className={styles.progressBar}
                        style={{
                          width: `${
                            s.progress.total
                              ? Math.min(100, (s.progress.current / s.progress.total) * 100)
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                  ) : null}
                  {s.note ? <div className={styles.stageNote}>{s.note}</div> : null}
                </div>
              </li>
            );
          })}
        </ol>

        <div className={styles.console} ref={scrollRef} role="log">
          {logs.length === 0 ? (
            <div className={styles.consoleEmpty}>
              日志会在这里逐行打印，跑一次就有内容。
            </div>
          ) : (
            logs.map((line) => (
              <div key={line.id} className={styles.logLine} data-tone={line.tone}>
                <span className={styles.logStage}>{line.stage}</span>
                <span className={styles.logText}>{line.text}</span>
              </div>
            ))
          )}
        </div>

        {llmStream.text ? (
          <div className={styles.llmStream} aria-label="LLM 输出流">
            <div className={styles.llmStreamHead}>
              <span>LLM · {llmStream.stage ?? ""}</span>
              <span data-numeric>{llmStream.text.length} 字符</span>
            </div>
            <div className={styles.llmStreamBody}>
              {llmStream.text}
              <span className={styles.llmCaret} aria-hidden="true" />
            </div>
          </div>
        ) : null}

        {fatal ? <div className={styles.fatal}>{fatal}</div> : null}
      </section>
    </>
  );
}

// Back-compat: earlier import site used <AnalysisPipelinePanel />. Alias to trigger.
export const AnalysisPipelinePanel = AnalysisPipelineTrigger;

