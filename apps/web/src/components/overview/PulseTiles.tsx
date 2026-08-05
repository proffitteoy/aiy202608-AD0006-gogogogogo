import { formatNumber } from "@/lib/format";
import type { PlatformPulse } from "@/lib/types";

import { Sparkline } from "./Sparkline";
import styles from "./PulseTiles.module.css";

type Props = {
  pulse: PlatformPulse;
};

export function PulseTiles({ pulse }: Props) {
  return (
    <section className={styles.grid} aria-label="今日风险脉搏">
      <div className={styles.tile}>
        <p className="eyebrow">活跃事件</p>
        <p className={styles.value} data-numeric>
          {formatNumber(pulse.activeEvents)}
        </p>
      </div>
      <div className={styles.tile}>
        <p className="eyebrow">高风险</p>
        <p className={`${styles.value} ${styles.high}`} data-numeric>
          {formatNumber(pulse.highRiskEvents)}
        </p>
      </div>
      <div className={styles.tile}>
        <p className="eyebrow">待复核</p>
        <p className={styles.value} data-numeric>
          {formatNumber(pulse.pendingReview)}
        </p>
      </div>
      <div className={`${styles.tile} ${styles.wave}`}>
        <p className="eyebrow">过去 24h 热度峰值</p>
        <Sparkline data={pulse.heatWave} width={220} height={48} label="24 小时热度峰值" />
      </div>
    </section>
  );
}
