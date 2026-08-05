import Link from "next/link";

import { ScoreBadge } from "@/components/overview/ScoreBadge";
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
  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link href="/" className={styles.back} aria-label="返回总览">
          ← 返回
        </Link>

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
            <span className="eyebrow">Rule 3</span>
            <span className={styles.metaValue} data-numeric>
              {formatScore(detail.score.rawScore)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className="eyebrow">Rule 4</span>
            <span className={styles.metaValue} data-numeric>
              {formatScore(detail.score.calibratedScore)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className="eyebrow">置信度</span>
            <span className={styles.metaValue} data-numeric>
              {formatScore(detail.score.confidence)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className="eyebrow">评分区间</span>
            <span className={styles.metaValue} data-numeric>
              {formatScoreInterval(detail.score.scoreInterval)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className="eyebrow">证据</span>
            <span className={styles.metaValue} data-numeric>
              {sourceCount}
            </span>
          </div>
        </div>

        <button
          type="button"
          className={styles.reportBtn}
          disabled
          title="AnalysisSnapshot 与 Agent 2 Render 尚未接入"
        >
          生成报告
        </button>
      </div>
    </header>
  );
}
