"use client";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { formatDateTime, formatScore } from "@/lib/format";
import type { Availability, OpinionAttribution } from "@/lib/types";

import styles from "./OpinionCluster.module.css";

type Props = {
  items: OpinionAttribution[];
  status: Availability;
};

export function OpinionCluster({ items, status }: Props) {
  const { open } = useEvidence();

  if (status !== "available" || items.length === 0) {
    const degraded = status === "degraded";
    return (
      <div className={styles.degraded} role="status">
        <div className={styles.degradedText}>
          <p className={styles.degradedTitle}>
            {degraded ? "观点归因接口不可用" : "观点归因尚未生成"}
          </p>
          <p className={styles.degradedHint}>
            Agent 2 Analyze 没有可验证的观点产物，规则评分与证据浏览不受影响。
          </p>
        </div>
      </div>
    );
  }

  return (
    <ul className={styles.list}>
      {items.map((item) => (
        <li key={item.id} className={styles.item}>
          <span className={styles.rail} aria-hidden="true" />

          <div className={styles.head}>
            <span className={styles.tag} data-numeric>
              #{item.id.slice(0, 8)}
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
            <span>{item.stance}</span>
            <span>{item.emotion}</span>
            <span>{item.claimType}</span>
          </div>

          <div className={styles.footer}>
            <span className={styles.source}>
              {item.authoritative ? <span className={styles.authTag}>事实源</span> : null}
              {item.source} · {formatDateTime(item.publishedAt)}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}
