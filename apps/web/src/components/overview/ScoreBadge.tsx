import { formatScore } from "@/lib/format";
import type { EventScore } from "@/lib/types";

import styles from "./ScoreBadge.module.css";

type Props = {
  score: EventScore;
};

export function ScoreBadge({ score }: Props) {
  const value = score.calibratedScore ?? score.rawScore;
  const label =
    score.calibratedScore !== null
      ? `校准分 ${formatScore(score.calibratedScore)}`
      : score.rawScore !== null
        ? `基础分 ${formatScore(score.rawScore)}`
        : "评分未产出";

  return (
    <span
      className={`${styles.badge} ${styles[score.status]}`}
      aria-label={label}
      title={score.degradationReasons.join(", ") || undefined}
    >
      <span className={styles.dot} aria-hidden="true" />
      <span>{value === null ? "未评分" : label}</span>
    </span>
  );
}
