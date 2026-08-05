"use client";

import { useDeferredValue, useMemo, useState } from "react";

import styles from "./OverviewToolbar.module.css";

type RangeKey = "24h" | "7d" | "30d" | "all";

type Props = {
  onFilter?: (query: string, range: RangeKey) => void;
};

const RANGE_OPTIONS: { key: RangeKey; label: string }[] = [
  { key: "24h", label: "24 小时" },
  { key: "7d", label: "7 天" },
  { key: "30d", label: "30 天" },
  { key: "all", label: "全部" },
];

export function OverviewToolbar({ onFilter }: Props) {
  const [query, setQuery] = useState("");
  const [range, setRange] = useState<RangeKey>("all");
  const deferred = useDeferredValue(query);

  const notify = useMemo(() => {
    if (!onFilter) return () => {};
    return (q: string, r: RangeKey) => onFilter(q, r);
  }, [onFilter]);

  return (
    <section className={styles.bar} aria-label="事件筛选">
      <div className={styles.left}>
        <label className={styles.search}>
          <span className={styles.searchIcon} aria-hidden="true">
            ⌕
          </span>
          <input
            type="search"
            value={query}
            placeholder="搜索事件、实体、关键词或股票代码"
            onChange={(e) => {
              const next = e.target.value;
              setQuery(next);
              notify(next, range);
            }}
            aria-label="搜索事件"
          />
          {query ? (
            <button
              type="button"
              className={styles.searchClear}
              onClick={() => {
                setQuery("");
                notify("", range);
              }}
              aria-label="清除搜索"
            >
              ×
            </button>
          ) : null}
        </label>
      </div>

      <div className={styles.chipRow} role="group" aria-label="时间范围">
        {RANGE_OPTIONS.map((option) => (
          <button
            key={option.key}
            type="button"
            className={styles.chip}
            data-active={range === option.key}
            onClick={() => {
              setRange(option.key);
              notify(deferred, option.key);
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
    </section>
  );
}
