"use client";

import { useCallback, useEffect, useRef } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { useResize } from "@/hooks/use-resize";
import { baseChartOption, chartPalette } from "@/lib/chart-theme";
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

type HeatCell = {
  value: [number, number, number];
  row: ImpactMatrixRow;
  metricId: MetricId;
};

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

  return <ImpactMatrixChart rows={rows} />;
}

function ImpactMatrixChart({ rows }: { rows: ImpactMatrixRow[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<{ resize: () => void; dispose: () => void } | null>(null);
  const { open } = useEvidence();

  const onResize = useCallback(() => chartRef.current?.resize(), []);
  useResize(containerRef, onResize);

  useEffect(() => {
    let disposed = false;
    let handleResize: (() => void) | undefined;

    void (async () => {
      const echarts = await import("echarts");
      if (disposed || !containerRef.current) return;

      const chart = echarts.init(containerRef.current, undefined, {
        renderer: "canvas",
      });
      chartRef.current = chart;

      const entities = rows.map((row) => row.entityName);
      const data: HeatCell[] = rows.flatMap((row, columnIndex) =>
        metricRows.map((metric, rowIndex) => ({
          value: [columnIndex, rowIndex, metricValue(row, metric.id)],
          row,
          metricId: metric.id,
        })),
      );

      chart.setOption({
        ...baseChartOption,
        grid: { ...baseChartOption.grid, top: 56, right: 20, bottom: 84, left: 92 },
        tooltip: {
          ...baseChartOption.tooltip,
          formatter: (params: unknown) => {
            const datum = (params as { data?: HeatCell }).data;
            if (!datum) return "";
            const metric = metricRows.find((item) => item.id === datum.metricId);
            const row = datum.row;
            return [
              `<strong>${row.entityName}</strong>`,
              `${metric?.label ?? datum.metricId}: ${formatScore(datum.value[2])}`,
              `${directionLabels[row.direction] ?? row.direction} / ${horizonLabels[row.timeHorizon] ?? row.timeHorizon}`,
              `边 ${row.edgeCount} / 观点 ${row.opinionCount} / 证据 ${row.evidenceCount}`,
            ].join("<br/>");
          },
        },
        xAxis: {
          ...baseChartOption.xAxis,
          type: "category",
          data: entities,
          axisLabel: {
            ...baseChartOption.xAxis.axisLabel,
            interval: 0,
            rotate: entities.length > 4 ? 28 : 0,
          },
        },
        yAxis: {
          ...baseChartOption.yAxis,
          type: "category",
          data: metricRows.map((metric) => metric.label),
        },
        visualMap: {
          min: 0,
          max: 1,
          calculable: false,
          orient: "horizontal",
          left: "center",
          bottom: 8,
          text: ["高", "低"],
          textStyle: {
            color: chartPalette.textTertiary,
            fontFamily: baseChartOption.textStyle.fontFamily,
            fontSize: 12,
          },
          inRange: {
            color: [
              chartPalette.divergingNeutral,
              chartPalette.divergingPalePos,
              chartPalette.divergingPositive,
            ],
          },
        },
        series: [
          {
            type: "heatmap",
            data,
            label: {
              show: true,
              fontSize: 11,
              color: chartPalette.textPrimary,
              formatter: (params: unknown) => {
                const datum = (params as { data?: HeatCell }).data;
                return datum ? formatScore(datum.value[2], 0) : "";
              },
            },
            emphasis: {
              itemStyle: {
                borderColor: chartPalette.textPrimary,
                borderWidth: 1,
              },
            },
          },
        ],
      });

      chart.on("click", (params: unknown) => {
        const datum = (params as { data?: HeatCell }).data;
        if (datum?.row.evidenceIds.length) {
          open(datum.row.evidenceIds);
        }
      });

      handleResize = () => chart.resize();
      window.addEventListener("resize", handleResize);
    })();

    return () => {
      disposed = true;
      if (handleResize) window.removeEventListener("resize", handleResize);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, [open, rows]);

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <span className={styles.note}>点击单元格可打开对象关联证据</span>
      </div>
      <div ref={containerRef} className={styles.chart} />
      <div className={styles.summary}>
        {rows.slice(0, 4).map((row) => (
          <button
            key={row.entityId}
            type="button"
            className={styles.summaryItem}
            onClick={() => open(row.evidenceIds)}
            disabled={row.evidenceIds.length === 0}
          >
            <span className={styles.summaryName}>{row.entityName}</span>
            <span className={styles.summaryMeta}>
              {directionLabels[row.direction] ?? row.direction} /{" "}
              {horizonLabels[row.timeHorizon] ?? row.timeHorizon}
            </span>
            <span className={styles.summaryScore} data-numeric>
              {formatScore(row.compositeConfidence)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
