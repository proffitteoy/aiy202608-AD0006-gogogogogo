"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { formatDateTime, formatTime } from "@/lib/format";

import { useEvidence } from "./EvidenceContext";
import { HighlightedText } from "./HighlightedText";
import styles from "./EvidenceDrawer.module.css";

const tierLabel = {
  authoritative: "权威",
  media: "媒体",
  social: "社交",
} as const;

type EvidenceAction = "included" | "excluded" | "flagged";

const actionLabel: Record<EvidenceAction, string> = {
  included: "已纳入分析",
  excluded: "已排除",
  flagged: "已标记",
};

export function EvidenceDrawer() {
  const { isOpen, items, close } = useEvidence();
  const [actions, setActions] = useState<Record<string, EvidenceAction>>({});
  const [pickedId, setPickedId] = useState<string | null>(null);

  function setAction(id: string, next: EvidenceAction) {
    setActions((prev) => {
      // 二次点击同一按钮 = 撤销
      if (prev[id] === next) {
        const rest = { ...prev };
        delete rest[id];
        return rest;
      }
      return { ...prev, [id]: next };
    });
  }

  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, close]);

  // isOpen 初始为 false，所以 SSR 首帧永远走这一支；只有客户端交互后才会真正渲染 portal
  if (!isOpen || items.length === 0) return null;
  if (typeof document === "undefined") return null;

  // 优先使用用户主动选中的，否则默认第一条（无 effect）
  const activeItem =
    (pickedId ? items.find((i) => i.id === pickedId) : undefined) ?? items[0];
  const activeAction = actions[activeItem.id];

  return createPortal(
    <>
      <div className={styles.backdrop} onClick={close} aria-hidden="true" />
      <aside
        className={styles.drawer}
        role="dialog"
        aria-modal="true"
        aria-label="证据抽屉"
      >
        <header className={styles.head}>
          <div>
            <p className="eyebrow">证据</p>
            <p className={styles.headMeta} data-numeric>
              {items.length} 篇原文
            </p>
          </div>
          <button type="button" className={styles.close} onClick={close} aria-label="关闭">
            ×
          </button>
        </header>

        <div className={styles.body}>
          {/* --- 左栏：原文清单 --- */}
          <nav className={styles.list} aria-label="原文列表">
            {items.map((item) => {
              const action = actions[item.id];
              const isActive = item.id === activeItem.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`${styles.listItem} ${isActive ? styles.listItemActive : ""} ${action ? styles[`listItem-${action}`] : ""}`}
                  onClick={() => setPickedId(item.id)}
                >
                  <span
                    className={`${styles.listTier} ${styles[`tier-${item.sourceTier}`]}`}
                  >
                    {tierLabel[item.sourceTier]}
                  </span>
                  <span className={styles.listSource}>{item.source}</span>
                  <span className={styles.listTime} data-numeric>
                    {formatTime(item.publishedAt)}
                  </span>
                  <span className={styles.listTitle}>{item.title}</span>
                  {action && (
                    <span
                      className={styles.listActionDot}
                      data-action={action}
                      aria-label={actionLabel[action]}
                    />
                  )}
                </button>
              );
            })}
          </nav>

          {/* --- 右栏：当前选中原文详情 --- */}
          <article className={styles.detail}>
            <header className={styles.detailHead}>
              <div className={styles.detailMeta}>
                <span
                  className={`${styles.tier} ${styles[`tier-${activeItem.sourceTier}`]}`}
                >
                  {tierLabel[activeItem.sourceTier]}
                </span>
                <span className={styles.source}>{activeItem.source}</span>
                <span className={styles.time} data-numeric>
                  {formatDateTime(activeItem.publishedAt)}
                </span>
              </div>
              {activeAction && (
                <span className={styles.actionTag} data-action={activeAction}>
                  {actionLabel[activeAction]}
                </span>
              )}
            </header>

            <h3 className={styles.title}>{activeItem.title}</h3>

            {!activeItem.linkAlive && (
              <p className={styles.notice}>
                链接不可达 · 显示采集时的文本快照
              </p>
            )}
            {activeItem.machineTranslated && (
              <p className={styles.notice}>本段为机器翻译 · 仅供参考</p>
            )}

            <div className={styles.detailBody}>
              <HighlightedText
                text={activeItem.body}
                highlights={activeItem.citedSpans}
              />
            </div>

            <div className={styles.actions}>
              <button
                type="button"
                className={`${styles.actionBtn} ${styles.include}`}
                onClick={() => setAction(activeItem.id, "included")}
                aria-pressed={activeAction === "included"}
              >
                <span aria-hidden="true">✓</span> 纳入分析
              </button>
              <button
                type="button"
                className={`${styles.actionBtn} ${styles.exclude}`}
                onClick={() => setAction(activeItem.id, "excluded")}
                aria-pressed={activeAction === "excluded"}
              >
                <span aria-hidden="true">✗</span> 排除
              </button>
              <button
                type="button"
                className={`${styles.actionBtn} ${styles.flag}`}
                onClick={() => setAction(activeItem.id, "flagged")}
                aria-pressed={activeAction === "flagged"}
              >
                <span aria-hidden="true">⚑</span> 标记
              </button>
            </div>

            <footer className={styles.itemFoot}>
              <span data-numeric>
                快照 · {formatDateTime(activeItem.capturedAt)}
              </span>
              {activeItem.linkUrl && activeItem.linkAlive && (
                <a
                  href={activeItem.linkUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.sourceLink}
                >
                  源链接 ↗
                </a>
              )}
            </footer>
          </article>
        </div>
      </aside>
    </>,
    document.body,
  );
}
