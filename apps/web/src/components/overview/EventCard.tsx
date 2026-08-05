import Link from "next/link";

import { formatSignedPercent, formatSentiment, formatRatio, formatTime } from "@/lib/format";
import type { EventSummary } from "@/lib/types";

import { RiskBadge } from "./RiskBadge";
import { Sparkline } from "./Sparkline";
import styles from "./EventCard.module.css";

type Props = {
  event: EventSummary;
};

const strokeByRisk: Record<EventSummary["risk"], string> = {
  high: "var(--risk-high)",
  mid: "var(--risk-mid)",
  low: "var(--risk-low)",
};

export function EventCard({ event }: Props) {
  const positive = event.heatChangePercent >= 0;

  return (
    <Link href={`/event/${event.id}`} className={`${styles.card} ${styles[event.risk]}`}>
      <span className={styles.rail} aria-hidden="true" />

      <div className={styles.head}>
        <RiskBadge level={event.risk} />
        <span className={styles.time} data-numeric>
          {formatTime(event.publishedAt)}
        </span>
        {event.freshness?.staleMinutes ? (
          <span className={styles.stale}>
            ⏱ 数据延迟 {event.freshness.staleMinutes}min
          </span>
        ) : null}
      </div>

      <h3 className={styles.title}>{event.title}</h3>

      <div className={styles.meta}>
        <span data-numeric>{event.sourceCount} 篇原文</span>
        <span className={styles.dot} aria-hidden="true">·</span>
        <span data-numeric>{event.authoritativeSourceCount} 家权威源</span>
        <span className={styles.dot} aria-hidden="true">·</span>
        <span data-numeric>
          复核 {event.reviewed.done}/{event.reviewed.total}
        </span>
      </div>

      <div className={styles.footer}>
        {event.risk !== "low" && (
          <div className={styles.spark}>
            <Sparkline
              data={event.sparkline}
              width={140}
              height={24}
              strokeColor={strokeByRisk[event.risk]}
            />
          </div>
        )}

        <div className={styles.metrics}>
          {event.risk !== "low" && (
            <>
              <span className={styles.metric}>
                情绪{" "}
                <strong data-numeric>{formatSentiment(event.sentiment)}</strong>
              </span>
              <span className={styles.metric}>
                多样性{" "}
                <strong data-numeric>{formatRatio(event.diversity)}</strong>
              </span>
            </>
          )}
          <span
            className={`${styles.heat} ${positive ? styles.heatUp : styles.heatDown}`}
            data-numeric
          >
            {formatSignedPercent(event.heatChangePercent)}
            <span aria-hidden="true">{positive ? "▲" : "▼"}</span>
          </span>
        </div>
      </div>
    </Link>
  );
}
