"use client";

import { useCallback, useEffect, useRef } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { AnalyzingBadge } from "@/components/ui/AnalyzingBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { usePanelReady } from "@/hooks/use-panel-ready";
import { useResize } from "@/hooks/use-resize";
import { baseChartOption, chartPalette } from "@/lib/chart-theme";
import type { TimelinePoint } from "@/lib/types";

import styles from "./Timeline.module.css";

type Props = {
  points: TimelinePoint[];
};

/**
 * ECharts 时间线 + 情绪带。ECharts 在客户端首次挂载时 lazy import 并初始化。
 */
export function Timeline({ points }: Props) {
  const ready = usePanelReady(450);

  if (!ready) {
    return (
      <>
        <AnalyzingBadge />
        <Skeleton variant="timeline" />
      </>
    );
  }

  return <TimelineChart points={points} />;
}

function TimelineChart({ points }: { points: TimelinePoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<unknown>(null);
  const { open } = useEvidence();

  const onResize = useCallback(() => {
    const chart = chartRef.current as { resize?: () => void } | null;
    chart?.resize?.();
  }, []);
  useResize(containerRef, onResize);

  useEffect(() => {
    let disposed = false;
    let handleResize: (() => void) | undefined;

    (async () => {
      const echarts = await import("echarts");
      if (disposed || !containerRef.current) return;

      const chart = echarts.init(containerRef.current, undefined, {
        renderer: "canvas",
      });
      chartRef.current = chart;

      const times = points.map((p) => p.timestamp);
      const heats = points.map((p) => p.heat);
      const sentiments = points.map((p) => p.sentiment);

      const markPoints = points
        .filter((p) => p.label)
        .map((p) => ({
          name: p.label,
          coord: [p.timestamp, p.heat],
          evidenceIds: p.evidenceIds,
          itemStyle: { color: chartPalette.accent },
          label: { color: chartPalette.textPrimary, fontSize: 12 },
        }));

      chart.setOption({
        ...baseChartOption,
        grid: { ...baseChartOption.grid, top: 56 },
        xAxis: {
          ...baseChartOption.xAxis,
          type: "time",
          axisLabel: { ...baseChartOption.xAxis.axisLabel, formatter: "{HH}:{mm}" },
        },
        yAxis: [
          {
            ...baseChartOption.yAxis,
            name: "热度",
            nameGap: 16,
            nameTextStyle: {
              color: chartPalette.textSecondary,
              fontSize: 12,
              padding: [0, 0, 0, 4],
            },
            min: 0,
          },
          {
            ...baseChartOption.yAxis,
            name: "情绪",
            nameGap: 16,
            nameTextStyle: {
              color: chartPalette.textSecondary,
              fontSize: 12,
              padding: [0, 4, 0, 0],
            },
            min: -1,
            max: 1,
            position: "right",
            axisLabel: {
              ...baseChartOption.yAxis.axisLabel,
              formatter: (v: number) => v.toFixed(1),
            },
          },
        ],
        series: [
          {
            name: "热度",
            type: "line",
            smooth: true,
            symbol: "circle",
            symbolSize: 6,
            lineStyle: { color: chartPalette.viz[0], width: 2 },
            itemStyle: { color: chartPalette.viz[0] },
            areaStyle: {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: "rgba(38, 83, 201, 0.18)" },
                  { offset: 1, color: "rgba(38, 83, 201, 0)" },
                ],
              },
            },
            data: times.map((t, i) => [t, heats[i]]),
            markPoint: {
              symbol: "pin",
              symbolSize: 32,
              data: markPoints,
            },
          },
          {
            name: "情绪",
            type: "line",
            yAxisIndex: 1,
            smooth: true,
            symbol: "none",
            lineStyle: { color: chartPalette.viz[4], width: 1, type: "dashed" },
            itemStyle: { color: chartPalette.viz[4] },
            data: times.map((t, i) => [t, sentiments[i]]),
          },
        ],
      });

      chart.on("click", (params) => {
        const raw = params as { componentType?: string; data?: unknown };
        if (raw.componentType === "markPoint") {
          const data = raw.data as { evidenceIds?: string[] } | undefined;
          if (data?.evidenceIds?.length) {
            open(data.evidenceIds);
          }
        }
      });

      handleResize = () => chart.resize();
      window.addEventListener("resize", handleResize);
    })();

    return () => {
      disposed = true;
      if (handleResize) window.removeEventListener("resize", handleResize);
      const chart = chartRef.current;
      if (chart && typeof (chart as { dispose?: () => void }).dispose === "function") {
        (chart as { dispose: () => void }).dispose();
      }
      chartRef.current = null;
    };
  }, [points, open]);

  return (
    <div className={styles.wrap}>
      <div className={styles.legend} aria-hidden="true">
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: chartPalette.viz[0] }}
          />
          热度
        </span>
        <span className={styles.legendItem}>
          <span
            className={`${styles.legendSwatch} ${styles.legendSwatchDashed}`}
            style={{ color: chartPalette.viz[4] }}
          />
          情绪
        </span>
      </div>
      <div ref={containerRef} className={styles.chart} />
    </div>
  );
}
