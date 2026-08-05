"use client";

import { useState } from "react";

import styles from "./DegradedBanner.module.css";

type Props = {
  message?: string;
  hint?: string;
};

export function DegradedBanner({
  message = "语义分析暂不可用",
  hint = "规则引擎结果正常显示",
}: Props) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div className={styles.banner} role="status">
      <span className={styles.rail} aria-hidden="true" />
      <span className={styles.icon} aria-hidden="true">
        ⚠
      </span>
      <span className={styles.text}>
        <strong>{message}</strong>
        <span className={styles.hint}> · {hint}</span>
      </span>
      <button
        type="button"
        className={styles.close}
        onClick={() => setDismissed(true)}
        aria-label="收起降级提示"
      >
        ×
      </button>
    </div>
  );
}
