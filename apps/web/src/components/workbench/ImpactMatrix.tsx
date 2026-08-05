"use client";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { formatScore } from "@/lib/format";
import type { Availability, ImpactMatrixRow } from "@/lib/types";

import styles from "./ImpactMatrix.module.css";

type Props = {
  rows: ImpactMatrixRow[];
  status: Availability;
};

const metricRows = [
  { id: "compositeConfidence", label: "综合置信度" },
  { id: "impactStrength", label: "影响强度" },
  { id: "businessExposure", label: "业务暴露" },
  { id: "opinionSupport", label: "舆情支持" },
  { id: "factSupport", label: "事实支持" },
] as const;

type MetricId = (typeof metricRows)[number]["id"];

const directionLabels: Record<string, string> = {
  positive: "受益",
  negative: "受损",
  uncertain: "不确定",
  neutral: "中性",
};

const horizonLabels: Record<string, string> = {
  immediate: "即时",
  short: "短期",
  medium: "中期",
  long: "长期",
  unknown: "未知",
};

function metricValue(row: ImpactMatrixRow, metricId: MetricId): number {
  switch (metricId) {
    case "compositeConfidence":
      return row.compositeConfidence;
    case "impactStrength":
      return row.impactStrength;
    case "businessExposure":
      return row.businessExposure;
    case "opinionSupport":
      return row.opinionSupport;
    case "factSupport":
      return row.factSupport;
  }
}

export function ImpactMatrix({ rows, status }: Props) {
  if (status !== "available" || rows.length === 0) {
    const degraded = status === "degraded";
    return (
      <div className={styles.empty} role="status">
        <strong>{degraded ? "影响矩阵接口不可用" : "热力矩阵尚未生成"}</strong>
        <span>
          {degraded
            ? "当前无法读取影响对象，其余工作台数据仍可继续使用。"
            : "后端还没有足够的传导边和观点来生成热力矩阵。"}
        </span>
      </div>
    );
  }

  return <ImpactMatrixTable rows={rows} />;
}

function ImpactMatrixTable({ rows }: { rows: ImpactMatrixRow[] }) {
  const { open } = useEvidence();

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <span className={styles.note}>点击行首主体可打开对象关联证据</span>
        <div className={styles.legend} aria-label="方向颜色图例">
          <span className={styles.legendItem} data-tone="positive">
            <span className={styles.legendDot} aria-hidden="true" />受益
          </span>
          <span className={styles.legendItem} data-tone="negative">
            <span className={styles.legendDot} aria-hidden="true" />受损
          </span>
          <span className={styles.legendItem} data-tone="neutral">
            <span className={styles.legendDot} aria-hidden="true" />不确定
          </span>
        </div>
        <span className={styles.meta} data-numeric>
          {rows.length} 主体 × {metricRows.length} 维
        </span>
      </div>
      <div className={styles.tableScroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.corner} />
              {metricRows.map((metric) => (
                <th key={metric.id} scope="col" className={styles.metricHead}>
                  {metric.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const dirLabel = directionLabels[row.direction] ?? row.direction;
              const horizonLabel =
                horizonLabels[row.timeHorizon] ?? row.timeHorizon;
              const evidenceEmpty = row.evidenceIds.length === 0;
              return (
                <tr key={row.entityId} data-direction={row.direction}>
                  <th scope="row" className={styles.entityHead}>
                    <button
                      type="button"
                      className={styles.entityBtn}
                      onClick={() => open(row.evidenceIds)}
                      disabled={evidenceEmpty}
                      title={`${dirLabel} · ${horizonLabel} · 边 ${row.edgeCount} / 观点 ${row.opinionCount} / 证据 ${row.evidenceCount}`}
                    >
                      <span className={styles.entityName}>{row.entityName}</span>
                      <span className={styles.entityMeta}>
                        {dirLabel} · {horizonLabel}
                      </span>
                    </button>
                  </th>
                  {metricRows.map((metric) => {
                    const v = metricValue(row, metric.id);
                    const width = Math.max(0, Math.min(1, v)) * 100;
                    return (
                      <td key={metric.id} className={styles.cell}>
                        <span className={styles.value} data-numeric>
                          {formatScore(v, 0)}
                        </span>
                        <span
                          className={styles.bar}
                          aria-hidden="true"
                          style={{ width: `${width}%` }}
                        />
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
