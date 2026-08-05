"use client";

import { useState } from "react";

import { ScoreBadge } from "@/components/overview/ScoreBadge";
import { ReportModal } from "@/components/report/ReportModal";
import {
  formatDateTime,
  formatEventStatus,
  formatRelative,
  formatScore,
  formatScoreInterval,
  formatTime,
} from "@/lib/format";
import type { EventDetail } from "@/lib/types";

import styles from "./WorkbenchHeader.module.css";

type Props = {
  detail: EventDetail;
  sourceCount: number;
};

export function WorkbenchHeader({ detail, sourceCount }: Props) {
  const [reportOpen, setReportOpen] = useState(false);
  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <div className={styles.titleBlock}>
          <div className={styles.crumbs}>
            <ScoreBadge score={detail.score} />
            <span className={styles.status}>{formatEventStatus(detail.status)}</span>
            <span className={styles.time} data-numeric>
              {formatTime(detail.publishedAt)}
            </span>
            {detail.freshness?.updatedAt ? (
              <span
                className={styles.updated}
                title={formatDateTime(detail.freshness.updatedAt)}
              >
                最后更新{" "}
                <span data-numeric>{formatRelative(detail.freshness.updatedAt)}</span>
              </span>
            ) : null}
          </div>
          <h1 className={styles.title}>{detail.title}</h1>
        </div>
      </div>

      <div className={styles.right}>
        <div className={styles.meta}>
          <div className={styles.metaCell}>
            <span className={styles.metaLabel}>R3</span>
            <span className={styles.metaValue} data-numeric>
              {formatScore(detail.score.rawScore)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className={styles.metaLabel}>R4</span>
            <span className={styles.metaValue} data-numeric>
              {formatScore(detail.score.calibratedScore)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className={styles.metaLabel}>置信</span>
            <span className={styles.metaValue} data-numeric>
              {formatScore(detail.score.confidence)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className={styles.metaLabel}>区间</span>
            <span className={styles.metaValue} data-numeric>
              {formatScoreInterval(detail.score.scoreInterval)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className={styles.metaLabel}>证据</span>
            <span className={styles.metaValue} data-numeric>
              {sourceCount}
            </span>
          </div>
        </div>

        <button
          type="button"
          className={styles.reportBtn}
          onClick={() => setReportOpen(true)}
          title="打开研究报告预览（可打印 / 导出 PDF）"
        >
          生成报告
        </button>
      </div>

      {reportOpen ? (
        <ReportModal detail={detail} onClose={() => setReportOpen(false)} />
      ) : null}
    </header>
  );
}
