"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { formatDateTime, formatTime } from "@/lib/format";

import { useEvidence } from "./EvidenceContext";
import { HighlightedText } from "./HighlightedText";
import styles from "./EvidenceDrawer.module.css";

const tierLabel = {
  authoritative: "事实",
  media: "新闻",
  social: "社交",
  market: "行情",
} as const;

export function EvidenceDrawer() {
  const { isOpen, items, close } = useEvidence();
  const [pickedId, setPickedId] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") close();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, close]);

  if (!isOpen || items.length === 0 || typeof document === "undefined") return null;

  const activeItem =
    (pickedId ? items.find((item) => item.id === pickedId) : undefined) ?? items[0];

  return createPortal(
    <div data-theme="dark">
      <div className={styles.backdrop} onClick={close} aria-hidden="true" />
      <aside
        className={styles.drawer}
        role="dialog"
        aria-modal="true"
        aria-label="证据抽屉"
      >
        <header className={styles.head}>
          <div className={styles.headBrand}>
            <span className={styles.headEyebrow}>EVIDENCE</span>
            <span className={styles.headMeta} data-numeric>
              {items.length}
              <em className={styles.headMetaUnit}>篇原文</em>
            </span>
          </div>
          <button type="button" className={styles.close} onClick={close} aria-label="关闭">
            ×
          </button>
        </header>

        <div className={styles.body}>
          <nav className={styles.list} aria-label="原文列表">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`${styles.listItem} ${item.id === activeItem.id ? styles.listItemActive : ""}`}
                onClick={() => setPickedId(item.id)}
              >
                <span className={`${styles.listTier} ${styles[`tier-${item.sourceTier}`]}`}>
                  {tierLabel[item.sourceTier]}
                </span>
                <span className={styles.listSource}>{item.source}</span>
                <span className={styles.listTime} data-numeric>
                  {formatTime(item.publishedAt)}
                </span>
                <span className={styles.listTitle}>{item.title}</span>
              </button>
            ))}
          </nav>

          <article className={styles.detail}>
            <header className={styles.detailHead}>
              <div className={styles.detailMeta}>
                <span className={`${styles.tier} ${styles[`tier-${activeItem.sourceTier}`]}`}>
                  {tierLabel[activeItem.sourceTier]}
                </span>
                <span className={styles.source}>{activeItem.source}</span>
                <span className={styles.time} data-numeric>
                  {formatDateTime(activeItem.publishedAt)}
                </span>
              </div>
            </header>

            <h3 className={styles.title}>{activeItem.title}</h3>

            {!activeItem.linkUrl ? (
              <p className={styles.notice}>来源未提供可访问链接，显示采集文本快照。</p>
            ) : null}

            <div className={styles.detailBody}>
              <HighlightedText
                text={activeItem.body}
                highlights={activeItem.citedSpans}
              />
            </div>

            <dl className={styles.provenance}>
              <div>
                <dt>采集时间</dt>
                <dd data-numeric>{formatDateTime(activeItem.capturedAt)}</dd>
              </div>
              <div>
                <dt>采集方式</dt>
                <dd>{activeItem.collectionMethod}</dd>
              </div>
              <div>
                <dt>许可范围</dt>
                <dd>{activeItem.licenseScope}</dd>
              </div>
            </dl>

            <footer className={styles.itemFoot}>
              <span data-numeric>evidence_id · {activeItem.id}</span>
              {activeItem.linkUrl ? (
                <a
                  href={activeItem.linkUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.sourceLink}
                >
                  打开源链接 ↗
                </a>
              ) : null}
            </footer>
          </article>
        </div>
      </aside>
    </div>,
    document.body,
  );
}
