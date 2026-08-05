import { formatNumber } from "@/lib/format";
import type { PlatformPulse } from "@/lib/types";

import styles from "./PulseTiles.module.css";

type TileConfig = {
  key: keyof PlatformPulse;
  label: string;
  hint: string;
  icon: string;
};

/** 主角瓦片放第一个，其余是陪衬 */
const TILES: TileConfig[] = [
  { key: "activeEvents", label: "活跃事件", hint: "正在监测的事件", icon: "◆" },
  { key: "totalEvents", label: "事件总量", hint: "所有生命周期", icon: "◇" },
  { key: "scoredEvents", label: "已完成校准", hint: "Rule 3/4 通过", icon: "▲" },
  { key: "documentCount", label: "关联原文", hint: "已入库文档", icon: "≡" },
];

type Props = {
  pulse: PlatformPulse;
};

export function PulseTiles({ pulse }: Props) {
  return (
    <div className={styles.strip} role="group" aria-label="平台脉搏">
      {TILES.map((tile) => (
        <article key={tile.key} className={styles.tile}>
          <span className={styles.icon} aria-hidden="true">
            {tile.icon}
          </span>
          <div className={styles.text}>
            <p className={styles.label}>{tile.label}</p>
            <p className={styles.hint}>{tile.hint}</p>
          </div>
          <p className={styles.value} data-numeric>
            {formatNumber(pulse[tile.key])}
          </p>
        </article>
      ))}
    </div>
  );
}
