import { formatNumber } from "@/lib/format";
import type { PlatformPulse } from "@/lib/types";

import styles from "./PulseTiles.module.css";

type Props = {
  pulse: PlatformPulse;
};

export function PulseTiles({ pulse }: Props) {
  return (
    <section className={styles.grid} aria-label="今日风险脉搏">
      <div className={styles.tile}>
        <p className="eyebrow">事件总数</p>
        <p className={styles.value} data-numeric>
          {formatNumber(pulse.totalEvents)}
        </p>
      </div>
      <div className={styles.tile}>
        <p className="eyebrow">活跃事件</p>
        <p className={styles.value} data-numeric>
          {formatNumber(pulse.activeEvents)}
        </p>
      </div>
      <div className={styles.tile}>
        <p className="eyebrow">已完成校准</p>
        <p className={styles.value} data-numeric>
          {formatNumber(pulse.scoredEvents)}
        </p>
      </div>
      <div className={styles.tile}>
        <p className="eyebrow">关联原文</p>
        <p className={styles.value} data-numeric>
          {formatNumber(pulse.documentCount)}
        </p>
      </div>
    </section>
  );
}
