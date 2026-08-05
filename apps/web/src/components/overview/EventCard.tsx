import Link from "next/link";

import {
  formatEventStatus,
  formatScore,
  formatScoreInterval,
} from "@/lib/format";
import type { EventSummary } from "@/lib/types";

import { ScoreBadge } from "./ScoreBadge";
import styles from "./EventCard.module.css";

type Props = {
  event: EventSummary;
};

const SOURCE_TYPE_COLORS: Record<string, string> = {
  fact: "var(--risk-low)",
  official: "var(--risk-low)",
  news: "var(--viz-1)",
  media: "var(--viz-1)",
  social: "var(--viz-2)",
  market: "var(--viz-3)",
};

function formatDayOnly(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function formatHourMinute(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function EventCard({ event }: Props) {
  const total = Object.values(event.sourceBreakdown).reduce((sum, v) => sum + v, 0) || 1;
  const segments = Object.entries(event.sourceBreakdown).sort((a, b) => b[1] - a[1]);
  const isActive = event.status.toLowerCase() === "active";

  return (
    <Link href={`/event/${event.id}`} className={styles.row}>
      <div className={styles.time} data-numeric>
        <span className={styles.timeMain}>{formatDayOnly(event.publishedAt)}</span>
        <span className={styles.timeSub}>{formatHourMinute(event.publishedAt)}</span>
      </div>

      <div className={styles.main}>
        <h3 className={styles.title}>{event.title}</h3>
        <div className={styles.tags}>
          <span className={styles.tag} data-tone={isActive ? "active" : "default"}>
            {formatEventStatus(event.status)}
          </span>
          <ScoreBadge score={event.score} />
        </div>
      </div>

      <div className={styles.sources}>
        <div className={styles.sourcesCount}>
          <span data-numeric>{event.sourceCount}</span>
          <span className={styles.sourcesLabel}>篇原文 · {segments.length} 类</span>
        </div>
        <div className={styles.sourcesBar} aria-hidden="true">
          {segments.map(([type, count]) => (
            <span
              key={type}
              className={styles.sourcesSeg}
              title={`${type} · ${count}`}
              style={{
                width: `${(count / total) * 100}%`,
                background: SOURCE_TYPE_COLORS[type] ?? "var(--text-tertiary)",
              }}
            />
          ))}
        </div>
      </div>

      <div className={styles.scores}>
        <div className={styles.scoreCell}>
          <span className={styles.scoreLabel}>R3</span>
          <span className={styles.scoreValue} data-numeric>
            {formatScore(event.score.rawScore)}
          </span>
        </div>
        <div className={styles.scoreCell}>
          <span className={styles.scoreLabel}>R4</span>
          <span className={styles.scoreValue} data-numeric>
            {formatScore(event.score.calibratedScore)}
          </span>
        </div>
        <div className={styles.scoreCell}>
          <span className={styles.scoreLabel}>置信</span>
          <span className={styles.scoreValue} data-numeric>
            {formatScore(event.score.confidence)}
          </span>
        </div>
        <div className={styles.scoreCell}>
          <span className={styles.scoreLabel}>区间</span>
          <span className={styles.scoreValue} data-numeric>
            {formatScoreInterval(event.score.scoreInterval)}
          </span>
        </div>
      </div>

      <span className={styles.chevron} aria-hidden="true">
        ›
      </span>
    </Link>
  );
}
