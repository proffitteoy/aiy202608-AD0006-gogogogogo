import { formatDateTime } from "@/lib/format";

import styles from "./Header.module.css";

type Props = {
  activeEventCount?: number;
  highRiskCount?: number;
  now?: Date;
};

export function Header({
  activeEventCount = 0,
  highRiskCount = 0,
  now = new Date(),
}: Props) {
  const timestamp = formatDateTime(now.toISOString());

  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">
          ◆
        </span>
        <span className={styles.brandName}>RiskTrace</span>
      </div>

      <div className={styles.meta}>
        <span className={styles.metaCell} data-numeric>
          {timestamp}
        </span>
        <span className={styles.divider} aria-hidden="true">
          ·
        </span>
        <span className={styles.metaCell}>
          活跃事件{" "}
          <strong data-numeric>{activeEventCount}</strong>
        </span>
        <span className={styles.divider} aria-hidden="true">
          ·
        </span>
        <span className={styles.metaCell}>
          高风险{" "}
          <strong className={styles.highRisk} data-numeric>
            {highRiskCount}
          </strong>
        </span>
      </div>
    </header>
  );
}
