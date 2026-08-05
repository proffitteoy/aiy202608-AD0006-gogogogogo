"use client";

import { useState } from "react";

import styles from "./DegradedBanner.module.css";

type Props = {
  message?: string;
  hint?: string;
};

export function DegradedBanner({
  message = "部分接口降级",
  hint = "规则引擎结果正常显示",
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className={styles.wrap} role="status">
      <button
        type="button"
        className={`status-pill ${styles.pill}`}
        data-tone="warn"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span aria-hidden="true">⚠</span>
        <span>{message}</span>
        <span className={styles.chev} aria-hidden="true">
          {expanded ? "▴" : "▾"}
        </span>
      </button>
      {expanded ? (
        <div className={styles.tray} role="note">
          <p className={styles.trayText}>{hint}</p>
          <button
            type="button"
            className={styles.trayClose}
            onClick={() => setDismissed(true)}
            aria-label="不再显示此降级提示"
          >
            不再显示
          </button>
        </div>
      ) : null}
    </div>
  );
}
