import Link from "next/link";

import {
  formatEventStatus,
  formatScore,
  formatScoreInterval,
  formatTime,
} from "@/lib/format";
import type { EventSummary } from "@/lib/types";

import { ScoreBadge } from "./ScoreBadge";
import styles from "./EventCard.module.css";

type Props = {
  event: EventSummary;
};

export function EventCard({ event }: Props) {
  return (
    <Link href={`/event/${event.id}`} className={styles.card}>
      <span className={styles.rail} aria-hidden="true" />

      <div className={styles.head}>
        <ScoreBadge score={event.score} />
        <span className={styles.status}>{formatEventStatus(event.status)}</span>
        <span className={styles.time} data-numeric>
          {formatTime(event.publishedAt)}
        </span>
      </div>

      <h3 className={styles.title}>{event.title}</h3>

      <div className={styles.meta}>
        <span data-numeric>{event.sourceCount} 篇原文</span>
        <span className={styles.dot} aria-hidden="true">·</span>
        <span data-numeric>{event.authoritativeSourceCount} 篇事实源</span>
        <span className={styles.dot} aria-hidden="true">·</span>
        <span data-numeric>{Object.keys(event.sourceBreakdown).length} 类来源</span>
      </div>

      <div className={styles.scores}>
        <span>
          <small>Rule 3</small>
          <strong data-numeric>{formatScore(event.score.rawScore)}</strong>
        </span>
        <span>
          <small>Rule 4</small>
          <strong data-numeric>{formatScore(event.score.calibratedScore)}</strong>
        </span>
        <span>
          <small>置信度</small>
          <strong data-numeric>{formatScore(event.score.confidence)}</strong>
        </span>
        <span>
          <small>评分区间</small>
          <strong data-numeric>{formatScoreInterval(event.score.scoreInterval)}</strong>
        </span>
      </div>
    </Link>
  );
}
