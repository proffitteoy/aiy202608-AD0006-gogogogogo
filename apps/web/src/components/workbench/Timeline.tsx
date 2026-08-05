"use client";

import { useCallback, useEffect, useRef } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { useResize } from "@/hooks/use-resize";
import { useIsDark } from "@/hooks/use-theme";
import {
  baseChartOption as baseLightOption,
  baseDarkChartOption,
  chartPalette as lightPalette,
  darkChartPalette,
} from "@/lib/chart-theme";
import type { TimelinePoint } from "@/lib/types";

import styles from "./Timeline.module.css";

type Props = {
  points: TimelinePoint[];
};

export function Timeline({ points }: Props) {
  if (points.length === 0) {
    return (
      <div className={styles.empty} role="status">
        暂无可核对的时间点数据
      </div>
    );
  }
  return <TimelineChart points={points} />;
}

function TimelineChart({ points }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<{ resize: () => void; dispose: () => void } | null>(null);
  const { open } = useEvidence();
  const isDark = useIsDark(containerRef);
  const palette = isDark ? darkChartPalette : lightPalette;
  const base = isDark ? baseDarkChartOption : baseLightOption;

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
          itemStyle: { color: palette.accent },
          label: { color: palette.textPrimary, fontSize: 12 },
        }));

      const series: unknown[] = [
        {
          name: "事件量",
          type: "line",
          smooth: 0.35,
          symbol: "circle",
          symbolSize: 7,
          showSymbol: true,
          sampling: "lttb",
          lineStyle: {
            color: palette.viz[0],
            width: 2.2,
            shadowColor: "rgba(38, 83, 201, 0.25)",
            shadowBlur: 6,
            shadowOffsetY: 2,
          },
          itemStyle: {
            color: "#fff",
            borderColor: palette.viz[0],
            borderWidth: 2,
          },
          emphasis: {
            focus: "series",
            scale: 1.6,
            itemStyle: {
              color: palette.viz[0],
              borderColor: "#fff",
              borderWidth: 2,
              shadowColor: "rgba(38, 83, 201, 0.55)",
              shadowBlur: 12,
            },
            lineStyle: { width: 2.8 },
          },
          areaStyle: {
            origin: "start",
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(38, 83, 201, 0.28)" },
                { offset: 0.55, color: "rgba(38, 83, 201, 0.1)" },
                { offset: 1, color: "rgba(38, 83, 201, 0)" },
              ],
            },
          },
          data: points.map((point) => ({
            value: [point.timestamp, point.documentCount],
            evidenceIds: point.evidenceIds,
            label: point.label,
            cursor: point.evidenceIds.length > 0 ? "pointer" : "default",
          })),
          markPoint: {
            symbol: "pin",
            symbolSize: 34,
            itemStyle: { color: palette.accent, opacity: 0.92 },
            emphasis: {
              scale: true,
              itemStyle: {
                shadowColor: "rgba(47, 79, 182, 0.45)",
                shadowBlur: 14,
              },
            },
            data: markPoints,
          },
          animationDuration: 900,
          animationEasing: "cubicOut",
        },
      ];
      if (hasSentiment) {
        series.push({
          name: "观点情绪",
          type: "line",
          yAxisIndex: 1,
          smooth: 0.35,
          symbol: "emptyCircle",
          symbolSize: 5,
          connectNulls: false,
          lineStyle: { color: palette.viz[4], width: 1.4, type: "dashed" },
          itemStyle: { color: palette.viz[4] },
          emphasis: {
            focus: "series",
            scale: 1.6,
            lineStyle: { width: 2 },
            itemStyle: {
              shadowColor: "rgba(209, 58, 72, 0.4)",
              shadowBlur: 10,
            },
          },
          data: points.map((point) => [point.timestamp, point.sentiment]),
          animationDuration: 900,
          animationEasing: "cubicOut",
        });
      }

      const eventIndexByTs = new Map<number, number>(
        points.map((p, i) => [new Date(p.timestamp).getTime(), i]),
      );
      const tooltipFormatter = (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        if (!items.length) return "";
        const first = items[0] as { axisValueLabel?: string; axisValue?: number };
        const stamp = new Date(first.axisValue ?? 0);
        const idx = eventIndexByTs.get(stamp.getTime());
        const point = idx !== undefined ? points[idx] : undefined;
        const timeStr = stamp.toLocaleString("zh-CN", {
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
        const rows = items
          .map((raw: unknown) => {
            const r = raw as {
              seriesName?: string;
              marker?: string;
              value?: [string, number | null];
            };
            const value = r.value?.[1];
            if (value === null || value === undefined) return "";
            const display =
              r.seriesName === "观点情绪"
                ? (value as number).toFixed(2)
                : String(value);
            return `<div style="display:flex;justify-content:space-between;gap:14px;margin-top:4px;">
              <span style="color:${palette.textSecondary};">${r.marker ?? ""}${r.seriesName}</span>
              <strong style="font-variant-numeric:tabular-nums;color:${palette.textPrimary};">${display}</strong>
            </div>`;
          })
          .join("");
        const label = point?.label
          ? `<div style="margin-top:6px;padding-top:6px;border-top:1px dashed ${palette.gridLine};color:${palette.textSecondary};font-size:12px;">锚点 · ${point.label}</div>`
          : "";
        const clickHint =
          point && point.evidenceIds.length > 0
            ? `<div style="margin-top:6px;color:${palette.textTertiary};font-size:11px;letter-spacing:0.02em;">点击查看 ${point.evidenceIds.length} 条证据</div>`
            : "";
        return `<div style="min-width:180px;font-size:12px;">
          <div style="color:${palette.textPrimary};font-weight:600;letter-spacing:0.02em;">${timeStr}</div>
          ${rows}
          ${label}
          ${clickHint}
        </div>`;
      };

      chart.setOption({
        ...base,
        grid: { top: 44, right: 28, bottom: 40, left: 52, containLabel: true },
        tooltip: {
          ...base.tooltip,
          trigger: "axis",
          axisPointer: {
            type: "cross",
            snap: true,
            label: {
              backgroundColor: palette.textPrimary,
              color: "#fff",
              fontSize: 11,
              padding: [4, 6],
              borderRadius: 3,
            },
            lineStyle: {
              color: palette.textTertiary,
              type: "dashed",
              width: 1,
            },
            crossStyle: {
              color: palette.textTertiary,
              type: "dashed",
              width: 1,
            },
          },
          formatter: tooltipFormatter,
        },
        xAxis: {
          ...base.xAxis,
          type: "time",
          boundaryGap: false,
          axisLabel: { ...base.xAxis.axisLabel, formatter: "{HH}:{mm}" },
          splitLine: {
            show: true,
            lineStyle: { color: palette.gridLine, type: "dashed", opacity: 0.35 },
          },
        },
        yAxis: [
          {
            ...base.yAxis,
            min: 0,
            minInterval: 1,
            splitLine: {
              lineStyle: { color: palette.gridLine, type: "dashed", opacity: 0.5 },
            },
          },
          {
            ...base.yAxis,
            show: hasSentiment,
            min: -1,
            max: 1,
            position: "right",
            splitLine: { show: false },
          },
        ],
        series,
      });

      chart.on("click", (params: unknown) => {
        const raw = params as {
          componentType?: string;
          seriesName?: string;
          data?: unknown;
        };
        // markPoint（顶部水滴 pin）和主 series 数据点（圆圈）都要能点开
        const isMarkPoint = raw.componentType === "markPoint";
        const isEventSeries =
          raw.componentType === "series" && raw.seriesName === "事件量";
        if (!isMarkPoint && !isEventSeries) return;
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
  }, [points, open, palette, base]);

  const hasSentiment = points.some((point) => point.sentiment !== null);
  return (
    <div className={styles.wrap}>
      <div className={styles.legend} aria-hidden="true">
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: palette.viz[0] }}
          />
          事件量
        </span>
        {hasSentiment ? (
          <span className={styles.legendItem}>
            <span
              className={`${styles.legendSwatch} ${styles.legendSwatchDashed}`}
              style={{ color: palette.viz[4] }}
            />
            观点情绪
          </span>
        ) : null}
      </div>
      <div ref={containerRef} className={styles.chart} />
    </div>
  );
}
