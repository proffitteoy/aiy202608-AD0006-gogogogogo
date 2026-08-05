"use client";

import { useCallback, useState } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { useOpinionDecisions } from "@/hooks/use-opinion-decisions";
import { formatDateTime, formatScore } from "@/lib/format";
import type { Availability, OpinionAttribution } from "@/lib/types";

import styles from "./OpinionCluster.module.css";

type Props = {
  items: OpinionAttribution[];
  status: Availability;
};

const STANCE_LABELS: Record<string, string> = {
  bullish: "看多",
  bearish: "看空",
  wait: "观望",
  neutral: "中性",
  positive: "正面",
  negative: "负面",
};

const EMOTION_LABELS: Record<string, string> = {
  optimistic: "乐观",
  negative: "负面",
  neutral: "中性",
  angry: "愤怒",
  fearful: "担忧",
  confident: "笃定",
};

const CLAIM_TYPE_LABELS: Record<string, string> = {
  opinion: "观点",
  speculation: "推测",
  fact: "事实陈述",
  question: "疑问",
};

function localize(raw: string, dict: Record<string, string>): string {
  return dict[raw.toLowerCase()] ?? raw;
}

export function OpinionCluster({ items, status }: Props) {
  const { open } = useEvidence();
  const { getState, setDecision, setNote } = useOpinionDecisions();
  const [noteOpenId, setNoteOpenId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const startNote = useCallback(
    (id: string) => {
      const existing = getState(id).note;
      setDraft(existing);
      setNoteOpenId(id);
    },
    [getState],
  );

  const saveNote = useCallback(
    (id: string) => {
      setNote(id, draft.trim());
      setNoteOpenId(null);
    },
    [draft, setNote],
  );

  if (status !== "available" || items.length === 0) {
    const degraded = status === "degraded";
    return (
      <div className={styles.degraded} role="status">
        <div className={styles.degradedText}>
          <p className={styles.degradedTitle}>
            {degraded ? "观点归因接口不可用" : "观点归因尚未生成"}
          </p>
          <p className={styles.degradedHint}>
            系统尚未产出可验证的观点归因结果，规则评分与证据浏览不受影响。
          </p>
        </div>
      </div>
    );
  }

  return (
    <ul className={styles.list}>
      {items.map((item, index) => {
        const state = getState(item.id);
        const isIncluded = state.decision === "include";
        const isExcluded = state.decision === "exclude";
        const hasNote = state.note.length > 0;
        const noteEditing = noteOpenId === item.id;
        const itemClass = [styles.item, isExcluded ? styles.excluded : ""]
          .filter(Boolean)
          .join(" ");

        return (
          <li key={item.id} className={itemClass}>
            <span className={styles.rail} data-tone={state.decision ?? "default"} aria-hidden="true" />

            <div className={styles.head}>
              <span className={styles.tag} data-numeric>
                {String(index + 1).padStart(2, "0")}
              </span>
              <button
                type="button"
                className={styles.label}
                onClick={() => open(item.evidenceIds)}
              >
                {item.reason}
              </button>
              <span className={styles.support} data-numeric>
                {formatScore(item.confidence, 0)}
              </span>
            </div>

            <div className={styles.supportBar} aria-hidden="true">
              <div
                className={styles.supportFill}
                style={{ width: `${item.confidence * 100}%` }}
              />
            </div>

            <p className={styles.excerpt}>{item.excerpt}</p>

            <div className={styles.attributes}>
              <span title={`stance: ${item.stance}`}>
                {localize(item.stance, STANCE_LABELS)}
              </span>
              <span title={`emotion: ${item.emotion}`}>
                {localize(item.emotion, EMOTION_LABELS)}
              </span>
              <span title={`claim_type: ${item.claimType}`}>
                {localize(item.claimType, CLAIM_TYPE_LABELS)}
              </span>
            </div>

            <div className={styles.footer}>
              <span className={styles.source}>
                {item.authoritative ? (
                  <span className={styles.authTag}>事实源</span>
                ) : null}
                {item.source} · {formatDateTime(item.publishedAt)}
              </span>

              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.confirmBtn}
                  aria-pressed={isIncluded}
                  onClick={() =>
                    setDecision(item.id, isIncluded ? null : "include")
                  }
                  title="将该观点纳入本次结论使用"
                >
                  {isIncluded ? "✓ 已纳入" : "纳入分析"}
                </button>
                <button
                  type="button"
                  className={styles.rejectBtn}
                  aria-pressed={isExcluded}
                  onClick={() =>
                    setDecision(item.id, isExcluded ? null : "exclude")
                  }
                  title="将该观点从本次结论中剔除"
                >
                  {isExcluded ? "✕ 已排除" : "排除"}
                </button>
                <button
                  type="button"
                  className={styles.noteBtn}
                  aria-pressed={hasNote || noteEditing}
                  onClick={() =>
                    noteEditing ? setNoteOpenId(null) : startNote(item.id)
                  }
                  title={hasNote ? "编辑标记" : "添加标记备注"}
                >
                  {hasNote ? `● 标记` : "标记"}
                </button>
              </div>
            </div>

            {noteEditing ? (
              <div className={styles.noteWrap}>
                <textarea
                  className={styles.noteInput}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="给这条观点加一段研判说明（仅本地保存，不上传后端）"
                  autoFocus
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                      e.preventDefault();
                      saveNote(item.id);
                    }
                    if (e.key === "Escape") {
                      e.preventDefault();
                      setNoteOpenId(null);
                    }
                  }}
                />
                <div className={styles.noteActions}>
                  <span className={styles.noteHint}>Ctrl+Enter 保存 · Esc 取消</span>
                  {hasNote ? (
                    <button
                      type="button"
                      className={styles.noteCancel}
                      onClick={() => {
                        setNote(item.id, "");
                        setDraft("");
                        setNoteOpenId(null);
                      }}
                    >
                      清空
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className={styles.noteCancel}
                    onClick={() => setNoteOpenId(null)}
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    className={styles.noteSave}
                    disabled={draft.trim() === state.note}
                    onClick={() => saveNote(item.id)}
                  >
                    保存
                  </button>
                </div>
              </div>
            ) : hasNote ? (
              <p className={styles.noteDisplay}>
                <span className={styles.noteDisplayLabel}>研判</span>
                {state.note}
              </p>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
