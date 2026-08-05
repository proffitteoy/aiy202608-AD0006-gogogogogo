"use client";

import { useCallback, useMemo, useState } from "react";

import { useHiddenEventIds } from "@/hooks/use-hidden-event-ids";
import type { EventSummary } from "@/lib/types";

import { EventCard } from "./EventCard";
import { OverviewToolbar } from "./OverviewToolbar";
import styles from "./OverviewStream.module.css";

type Props = {
  events: EventSummary[];
};

type RangeKey = "24h" | "7d" | "30d" | "all";

const RANGE_MS: Record<RangeKey, number> = {
  "24h": 24 * 60 * 60 * 1000,
  "7d": 7 * 24 * 60 * 60 * 1000,
  "30d": 30 * 24 * 60 * 60 * 1000,
  all: Number.POSITIVE_INFINITY,
};

const RANGE_HINT: Record<RangeKey, string> = {
  "24h": "过去 24 小时",
  "7d": "过去 7 天",
  "30d": "过去 30 天",
  all: "全部记录",
};

function matchesQuery(event: EventSummary, query: string): boolean {
  if (!query) return true;
  const needle = query.toLowerCase();
  if (event.title.toLowerCase().includes(needle)) return true;
  if (event.id.toLowerCase().includes(needle)) return true;
  return Object.keys(event.sourceBreakdown).some((s) =>
    s.toLowerCase().includes(needle),
  );
}

function matchesRange(event: EventSummary, range: RangeKey, now: number): boolean {
  const window = RANGE_MS[range];
  if (!Number.isFinite(window)) return true;
  const published = new Date(event.publishedAt).getTime();
  return now - published <= window;
}

export function OverviewStream({ events }: Props) {
  const [query, setQuery] = useState("");
  const [range, setRange] = useState<RangeKey>("all");
  const { isHidden, hide, restoreAll, hiddenIds, hydrated } = useHiddenEventIds();

  const handleFilter = useCallback((q: string, r: RangeKey) => {
    setQuery(q);
    setRange(r);
  }, []);

  const filtered = useMemo(() => {
    const now = Date.now();
    return events.filter(
      (event) =>
        !isHidden(event.id) &&
        matchesQuery(event, query) &&
        matchesRange(event, range, now),
    );
  }, [events, query, range, isHidden]);

  const hiddenCount = hydrated ? hiddenIds.length : 0;

  return (
    <>
      <header className={styles.streamHeader}>
        <OverviewToolbar onFilter={handleFilter} />
      </header>
      {hiddenCount > 0 ? (
        <div className={styles.hiddenBanner} role="status">
          <span>已从演示中隐藏 {hiddenCount} 条</span>
          <button type="button" className={styles.restoreButton} onClick={restoreAll}>
            全部恢复
          </button>
        </div>
      ) : null}

      <section className={styles.tableWrap} aria-label="事件流列表">
        <div className={styles.head}>
          <span className={styles.headCell} style={{ width: 68 }}>
            时间
          </span>
          <span className={styles.headCell} style={{ flex: 1, minWidth: 0 }}>
            事件
          </span>
          <span
            className={styles.headCell}
            style={{ width: "clamp(120px, 15vw, 180px)" }}
          >
            来源结构
          </span>
          <span
            className={styles.headCell}
            style={{ width: "clamp(220px, 26vw, 280px)" }}
          >
            评分
          </span>
          <span
            className={styles.headCell}
            aria-hidden="true"
            style={{ width: 14 }}
          />
        </div>

        {filtered.length > 0 ? (
          <div className={styles.list}>
            {filtered.map((event, index) => (
              <div
                key={event.id}
                className={styles.item}
                style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
              >
                <EventCard event={event} onHide={hide} />
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.empty} role="status">
            <strong>{query ? "没有匹配的事件" : "暂无可展示事件"}</strong>
            <span>
              {query
                ? "试试换个关键词，或把时间范围切换回“全部”。"
                : "导入完成后，事件会从后端查询结果中出现。"}
            </span>
          </div>
        )}
      </section>
    </>
  );
}
