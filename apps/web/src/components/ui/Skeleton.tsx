import styles from "./Skeleton.module.css";

type Props = {
  variant?: "card" | "timeline" | "graph" | "line";
  width?: string | number;
  height?: string | number;
};

/**
 * 骨架屏。避免 spinner。
 * - card: 事件卡形态
 * - timeline: 12 根竖立骨架条，波动高度
 * - graph: 中心脉冲圆
 * - line: 单行文本骨架
 */
export function Skeleton({ variant = "line", width, height }: Props) {
  if (variant === "timeline") {
    return (
      <div className={styles.timeline} aria-hidden="true">
        {Array.from({ length: 12 }).map((_, i) => (
          <span
            key={i}
            className={styles.bar}
            style={{ height: `${30 + Math.abs(Math.sin(i * 0.9)) * 60}%` }}
          />
        ))}
      </div>
    );
  }

  if (variant === "graph") {
    return (
      <div className={styles.graph} aria-hidden="true">
        <span className={styles.pulse} />
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div className={styles.card} aria-hidden="true">
        <div className={styles.line} />
        <div className={styles.line} style={{ width: "60%" }} />
        <div className={styles.line} style={{ width: "40%" }} />
      </div>
    );
  }

  return (
    <div
      className={styles.line}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}
