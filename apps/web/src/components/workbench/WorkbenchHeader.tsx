"use client";

import Link from "next/link";
import { useState } from "react";

import { ReportModal } from "@/components/report/ReportModal";
import { RiskBadge } from "@/components/overview/RiskBadge";
import { formatDateTime, formatRelative, formatSentiment, formatTime } from "@/lib/format";
import type { EventDetail } from "@/lib/types";

import styles from "./WorkbenchHeader.module.css";

type Props = {
  detail: EventDetail;
  sourceCount: number;
  avgSentiment: number;
  reviewed: { done: number; total: number };
};

export function WorkbenchHeader({ detail, sourceCount, avgSentiment, reviewed }: Props) {
  const [reportOpen, setReportOpen] = useState(false);

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link href="/" className={styles.back} aria-label="返回总览">
          ← 返回
        </Link>

        <div className={styles.titleBlock}>
          <div className={styles.crumbs}>
            <RiskBadge level={detail.risk} />
            <span className={styles.time} data-numeric>
              {formatTime(detail.publishedAt)}
            </span>
            <span className={styles.version} data-numeric>
              v{detail.version}
            </span>
            {detail.freshness?.updatedAt && (
              <span
                className={styles.updated}
                title={formatDateTime(detail.freshness.updatedAt)}
              >
                最后更新{" "}
                <span data-numeric>{formatRelative(detail.freshness.updatedAt)}</span>
              </span>
            )}
          </div>
          <h1 className={styles.title}>{detail.title}</h1>
        </div>
      </div>

      <div className={styles.right}>
        <div className={styles.meta}>
          <div className={styles.metaCell}>
            <span className="eyebrow">来源</span>
            <span className={styles.metaValue} data-numeric>
              {sourceCount}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className="eyebrow">净情绪</span>
            <span
              className={`${styles.metaValue} ${
                avgSentiment < 0 ? styles.negative : styles.positive
              }`}
              data-numeric
            >
              {formatSentiment(avgSentiment)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className="eyebrow">复核</span>
            <span className={styles.metaValue} data-numeric>
              {reviewed.done}/{reviewed.total}
            </span>
          </div>
        </div>

        <button
          type="button"
          className={styles.reportBtn}
          onClick={() => setReportOpen(true)}
        >
          生成报告
        </button>
      </div>

      {reportOpen && (
        <ReportModal detail={detail} onClose={() => setReportOpen(false)} />
      )}
    </header>
  );
}
