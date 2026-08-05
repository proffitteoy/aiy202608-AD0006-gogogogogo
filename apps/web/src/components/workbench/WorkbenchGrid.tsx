"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import styles from "./WorkbenchGrid.module.css";

export type PanelId = "timeline" | "clusters" | "graph" | "impact";

type ExpandContextValue = {
  expandedId: PanelId | null;
  toggle: (id: PanelId) => void;
  collapse: () => void;
};

const ExpandContext = createContext<ExpandContextValue | null>(null);

function useExpand(): ExpandContextValue {
  const ctx = useContext(ExpandContext);
  if (!ctx) {
    throw new Error("WorkbenchPanel must be used inside <WorkbenchGrid>");
  }
  return ctx;
}

type PanelProps = {
  id: PanelId;
  /** @deprecated kept for prop compatibility; no longer rendered */
  eyebrow?: string;
  title: string;
  meta?: string;
  children: ReactNode;
};

const PANEL_ICONS: Record<PanelId, string> = {
  timeline: "◔",
  clusters: "◈",
  graph: "⇋",
  impact: "▦",
};

export function WorkbenchPanel({ id, title, meta, children }: PanelProps) {
  const { expandedId, toggle } = useExpand();
  const expanded = expandedId === id;
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (expanded) btnRef.current?.focus();
  }, [expanded]);

  return (
    <section className={styles.panel}>
      <header className={styles.panelHead}>
        <h2 className={styles.panelTitle}>
          <span className={styles.panelIcon} aria-hidden="true">
            {PANEL_ICONS[id]}
          </span>
          {title}
        </h2>
        <div className={styles.panelActions}>
          {meta ? <span className={styles.meta}>{meta}</span> : null}
          <button
            ref={btnRef}
            type="button"
            className={styles.expandBtn}
            aria-label={expanded ? "收起面板" : `放大 ${title}`}
            aria-pressed={expanded}
            onClick={() => toggle(id)}
          >
            <span aria-hidden="true">{expanded ? "×" : "⤢"}</span>
          </button>
        </div>
      </header>
      <div className={styles.panelBody}>{children}</div>
    </section>
  );
}

type GridProps = {
  timeline: ReactNode;
  clusters: ReactNode;
  graph: ReactNode;
  impact: ReactNode;
};

export function WorkbenchGrid({ timeline, clusters, graph, impact }: GridProps) {
  const [expandedId, setExpandedId] = useState<PanelId | null>(null);

  const toggle = useCallback((id: PanelId) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  const collapse = useCallback(() => setExpandedId(null), []);

  useEffect(() => {
    if (!expandedId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") collapse();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expandedId, collapse]);

  const cellClass = (id: PanelId) => {
    const parts = [styles.cell];
    if (expandedId === id) parts.push(styles.cellExpanded);
    else if (expandedId) parts.push(styles.cellHidden);
    return parts.join(" ");
  };

  const gridClass = `${styles.grid}${expandedId ? ` ${styles.gridExpanded}` : ""}`;

  return (
    <ExpandContext.Provider value={{ expandedId, toggle, collapse }}>
      <div className={gridClass}>
        <div className={cellClass("timeline")}>{timeline}</div>
        <div className={cellClass("clusters")}>{clusters}</div>
        <div className={cellClass("graph")}>{graph}</div>
        <div className={cellClass("impact")}>{impact}</div>
      </div>
    </ExpandContext.Provider>
  );
}
