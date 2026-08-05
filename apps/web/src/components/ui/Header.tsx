import styles from "./Header.module.css";

type Props = {
  activeEventCount?: number;
  scoredEventCount?: number;
};

export function Header({
  activeEventCount = 0,
  scoredEventCount = 0,
}: Props) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">
          ◆
        </span>
        <span className={styles.brandName}>RiskTrace</span>
      </div>

      <div className={styles.meta}>
        <span className={styles.metric} title="正在监测中的事件">
          <span className={styles.metricLabel}>活跃</span>
          <strong data-numeric>{activeEventCount}</strong>
        </span>
        <span className={styles.metric} title="已完成 Rule 3/4 校准的事件">
          <span className={styles.metricLabel}>已校准</span>
          <strong data-numeric>{scoredEventCount}</strong>
        </span>
      </div>
    </header>
  );
}
