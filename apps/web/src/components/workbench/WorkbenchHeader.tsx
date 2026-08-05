import { ScoreBadge } from "@/components/overview/ScoreBadge";
import { ReportLaunchButton } from "@/components/workbench/ReportLaunchButton";
import {
  formatEventStatus,
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
        <div className={styles.titleBlock}>
          <div className={styles.crumbs}>
            <ScoreBadge score={detail.score} />
            <span className={styles.status}>{formatEventStatus(detail.status)}</span>
            <span className={styles.time} data-numeric>
              {formatTime(detail.publishedAt)}
            </span>
          </div>
          <h1 className={styles.title}>{detail.title}</h1>
        </div>
      </div>

      <div className={styles.right}>
        <div className={styles.meta}>
          <div className={styles.metaCell}>
            <span className="eyebrow">原始评分</span>
            <span className={styles.metaValue} data-numeric>
              {formatScore(detail.score.rawScore)}
            </span>
          </div>
          <div className={styles.metaCell}>
            <span className="eyebrow">校准评分</span>
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

        <ReportLaunchButton eventId={detail.id} />
      </div>
    </header>
  );
}
