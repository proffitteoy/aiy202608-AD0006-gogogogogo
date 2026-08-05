import styles from "./StaleTag.module.css";

type Props = {
  minutes: number;
  updatedAt?: string;
};

export function StaleTag({ minutes, updatedAt }: Props) {
  return (
    <span
      className={styles.tag}
      title={updatedAt ? `最后更新：${updatedAt}` : undefined}
    >
      <span aria-hidden="true">⏱</span>
      数据延迟 <span data-numeric>{minutes}</span>min
    </span>
  );
}
