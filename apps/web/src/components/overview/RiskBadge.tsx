import type { RiskLevel } from "@/lib/types";

import styles from "./RiskBadge.module.css";

type Props = {
  level: RiskLevel;
  compact?: boolean;
};

const labels: Record<RiskLevel, string> = {
  high: "HIGH",
  mid: "MID",
  low: "LOW",
};

const arrows: Record<RiskLevel, string> = {
  high: "▲",
  mid: "▲",
  low: "▼",
};

export function RiskBadge({ level, compact = false }: Props) {
  return (
    <span className={`${styles.badge} ${styles[level]}`} aria-label={`风险 ${labels[level]}`}>
      <span aria-hidden="true">{arrows[level]}</span>
      {!compact && <span>{labels[level]}</span>}
    </span>
  );
}
