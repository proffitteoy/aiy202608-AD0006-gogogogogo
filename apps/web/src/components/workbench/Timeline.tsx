"use client";

import { useCallback, useEffect, useRef } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { useResize } from "@/hooks/use-resize";
import { baseChartOption, chartPalette } from "@/lib/chart-theme";
import type { TimelinePoint } from "@/lib/types";

import styles from "./Timeline.module.css";

type Props = {
  points: TimelinePoint[];
};

export function Timeline({ points }: Props) {
  if (points.length === 0) {
    return (
      <div className={styles.empty} role="status">
        暂无可核对的时间桶数据
      </div>
    );
  }
  return <TimelineChart points={points} />;
}

function TimelineChart({ points }: Props) {
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

      const hasSentiment = points.some((point) => point.sentiment !== null);
      const markPoints = points
        .filter((point) => point.label)
        .map((point) => ({
          name: point.label,
          coord: [point.timestamp, point.documentCount],
          evidenceIds: point.evidenceIds,
          itemStyle: { color: chartPalette.accent },
          label: { color: chartPalette.textPrimary, fontSize: 12 },
        }));

      const series: unknown[] = [
        {
          name: "文档量",
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
          data: points.map((point) => [point.timestamp, point.documentCount]),
          markPoint: {
            symbol: "pin",
            symbolSize: 32,
            data: markPoints,
          },
        },
      ];
      if (hasSentiment) {
        series.push({
          name: "观点情绪",
          type: "line",
          yAxisIndex: 1,
          smooth: true,
          symbol: "none",
          connectNulls: false,
          lineStyle: { color: chartPalette.viz[4], width: 1, type: "dashed" },
          itemStyle: { color: chartPalette.viz[4] },
          data: points.map((point) => [point.timestamp, point.sentiment]),
        });
      }

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
            name: "文档量",
            min: 0,
            minInterval: 1,
          },
          {
            ...baseChartOption.yAxis,
            show: hasSentiment,
            name: "情绪",
            min: -1,
            max: 1,
            position: "right",
          },
        ],
        series,
      });

      chart.on("click", (params: unknown) => {
        const raw = params as { componentType?: string; data?: unknown };
        if (raw.componentType !== "markPoint") return;
        const data = raw.data as { evidenceIds?: string[] } | undefined;
        if (data?.evidenceIds?.length) open(data.evidenceIds);
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
  }, [points, open]);

  const hasSentiment = points.some((point) => point.sentiment !== null);
  return (
    <div className={styles.wrap}>
      <div className={styles.legend} aria-hidden="true">
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: chartPalette.viz[0] }}
          />
          文档量
        </span>
        {hasSentiment ? (
          <span className={styles.legendItem}>
            <span
              className={`${styles.legendSwatch} ${styles.legendSwatchDashed}`}
              style={{ color: chartPalette.viz[4] }}
            />
            观点情绪
          </span>
        ) : null}
      </div>
      <div ref={containerRef} className={styles.chart} />
    </div>
  );
}
