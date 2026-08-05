import styles from "./AnalyzingBadge.module.css";

type Props = {
  label?: string;
};

/**
 * 骨架屏进场时的浮层提示，标注 "AI 分析中 · 约 5 秒"。
 * 不接管任何交互，纯装饰性。
 */
export function AnalyzingBadge({ label = "AI 分析中 · 约 5 秒" }: Props) {
  return (
    <div className={styles.badge} role="status" aria-live="polite">
      <span className={styles.pulse} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
