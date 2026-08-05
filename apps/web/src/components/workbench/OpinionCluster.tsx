"use client";

import { useState } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { AnalyzingBadge } from "@/components/ui/AnalyzingBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/ToastContext";
import { usePanelReady } from "@/hooks/use-panel-ready";
import { formatRelative } from "@/lib/format";
import type { OpinionCluster as ClusterType } from "@/lib/types";

import styles from "./OpinionCluster.module.css";

type Verdict = "pending" | "confirmed" | "rejected";

type Props = {
  clusters: ClusterType[];
  /** LLM 是否可用；false 时展示"语义分析暂不可用"覆盖 */
  llmAvailable?: boolean;
};

export function OpinionCluster({ clusters, llmAvailable = true }: Props) {
  const { open } = useEvidence();
  const { push } = useToast();
  const [verdicts, setVerdicts] = useState<Record<string, Verdict>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [expandedNoteId, setExpandedNoteId] = useState<string | null>(null);
  const ready = usePanelReady(550);
  // 骨架阶段：每 3 次操作演示一次"保存失败"，展示我们不假装存活
  const [saveAttempts, setSaveAttempts] = useState(0);

  function applyVerdict(id: string, next: Verdict) {
    const attempt = saveAttempts + 1;
    setSaveAttempts(attempt);
    // 每第 3 次触发失败演示
    if (attempt % 3 === 0) {
      push({
        kind: "error",
        title: "保存失败，请重试",
        hint: "网络连接不稳定 · 已保留当前选择",
        action: {
          label: "重试",
          onClick: () => {
            setVerdicts((prev) => ({ ...prev, [id]: next }));
            push({
              kind: "success",
              title: "已保存",
              hint: `观点 #${id.replace(/^c/, "")} 状态已同步`,
            });
          },
        },
      });
      // 失败态：保留 UI 选择但不"落库"——这里 UI 仍显示新状态，Toast 提示重试
      setVerdicts((prev) => ({ ...prev, [id]: next }));
      return;
    }
    setVerdicts((prev) => ({ ...prev, [id]: next }));
  }

  // LLM 不可用：直接展示降级覆盖，绕过骨架/内容
  if (!llmAvailable) {
    return (
      <div className={styles.degraded} role="status">
        <span className={styles.degradedIcon} aria-hidden="true">⚠</span>
        <div className={styles.degradedText}>
          <p className={styles.degradedTitle}>语义分析暂不可用</p>
          <p className={styles.degradedHint}>
            LLM 服务未就绪 · 时间线、传导图、影响矩阵仍基于规则引擎正常运行
          </p>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <>
        <AnalyzingBadge label="LLM 抽取观点簇 · 约 5 秒" />
        <div className={styles.skeletonStack}>
          <Skeleton variant="card" />
          <Skeleton variant="card" />
          <Skeleton variant="card" />
        </div>
      </>
    );
  }

  return (
    <ul className={styles.list}>
      {clusters.map((cluster) => {
        const verdict = verdicts[cluster.id] ?? "pending";
        return (
          <li
            key={cluster.id}
            className={`${styles.item} ${styles[verdict]}`}
          >
            <span className={styles.rail} aria-hidden="true" />

            <div className={styles.head}>
              <span className={styles.tag} data-numeric>
                #{cluster.id.replace(/^c/, "")}
              </span>
              <button
                type="button"
                className={styles.label}
                onClick={() => open(cluster.evidenceIds)}
              >
                {cluster.label}
              </button>
              <span className={styles.support} data-numeric>
                {Math.round(cluster.support * 100)}
              </span>
            </div>

            <div className={styles.supportBar} aria-hidden="true">
              <div
                className={styles.supportFill}
                style={{ width: `${cluster.support * 100}%` }}
              />
            </div>

            <p className={styles.excerpt}>{cluster.representativeExcerpt}</p>

            <div className={styles.footer}>
              <span className={styles.source}>
                {cluster.authoritative && (
                  <span className={styles.authTag}>权威</span>
                )}
                @{cluster.representativeSource} · {formatRelative(cluster.representativeAt)}
              </span>

              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.confirmBtn}
                  onClick={() => applyVerdict(cluster.id, "confirmed")}
                  aria-pressed={verdict === "confirmed"}
                >
                  ✓ 确认
                </button>
                <button
                  type="button"
                  className={styles.rejectBtn}
                  onClick={() => applyVerdict(cluster.id, "rejected")}
                  aria-pressed={verdict === "rejected"}
                >
                  ✗ 拒绝
                </button>
                <button
                  type="button"
                  className={styles.noteBtn}
                  onClick={() =>
                    setExpandedNoteId((prev) =>
                      prev === cluster.id ? null : cluster.id,
                    )
                  }
                  aria-pressed={
                    expandedNoteId === cluster.id || !!notes[cluster.id]
                  }
                >
                  {notes[cluster.id] ? "✎ 已备注" : "+ 备注"}
                </button>
              </div>
            </div>

            {expandedNoteId === cluster.id && (
              <div className={styles.noteWrap}>
                <textarea
                  className={styles.noteInput}
                  placeholder="写下你的判断理由或后续调查线索..."
                  value={notes[cluster.id] ?? ""}
                  onChange={(e) =>
                    setNotes((prev) => ({
                      ...prev,
                      [cluster.id]: e.target.value,
                    }))
                  }
                  rows={3}
                  autoFocus
                />
                <div className={styles.noteActions}>
                  <span className={styles.noteHint} data-numeric>
                    {notes[cluster.id]?.length ?? 0} / 500
                  </span>
                  <button
                    type="button"
                    className={styles.noteCancel}
                    onClick={() => {
                      setNotes((prev) => {
                        const rest = { ...prev };
                        delete rest[cluster.id];
                        return rest;
                      });
                      setExpandedNoteId(null);
                    }}
                  >
                    清除
                  </button>
                  <button
                    type="button"
                    className={styles.noteSave}
                    onClick={() => {
                      setExpandedNoteId(null);
                      push({
                        kind: "success",
                        title: "备注已保存",
                        hint: `观点 #${cluster.id.replace(/^c/, "")} 已附加研究员备注`,
                      });
                    }}
                    disabled={!notes[cluster.id]?.trim()}
                  >
                    保存
                  </button>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
