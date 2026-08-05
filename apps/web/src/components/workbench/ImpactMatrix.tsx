"use client";

import { useCallback, useEffect, useRef } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { AnalyzingBadge } from "@/components/ui/AnalyzingBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { usePanelReady } from "@/hooks/use-panel-ready";
import { useResize } from "@/hooks/use-resize";
import { baseChartOption, chartPalette } from "@/lib/chart-theme";
import type { ImpactMatrix as MatrixType } from "@/lib/types";

import styles from "./ImpactMatrix.module.css";

type Props = {
  matrix: MatrixType;
  cellEvidence?: (row: string, col: string) => string[];
};

export function ImpactMatrix({ matrix, cellEvidence }: Props) {
  const ready = usePanelReady(650);

  if (!ready) {
    return (
      <>
        <AnalyzingBadge label="AI 计算影响矩阵 · 约 5 秒" />
        <Skeleton variant="card" />
      </>
    );
  }

  return <ImpactMatrixChart matrix={matrix} cellEvidence={cellEvidence} />;
}

function ImpactMatrixChart({ matrix, cellEvidence }: Props) {
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

      const data: [number, number, number][] = [];
      matrix.cells.forEach((row, r) => {
        row.forEach((value, c) => {
          data.push([c, r, value]);
        });
      });

      chart.setOption({
        ...baseChartOption,
        animationDuration: 600,
        animationEasing: "cubicOut",
        grid: { top: 44, right: 20, bottom: 40, left: 128 },
        tooltip: {
          ...baseChartOption.tooltip,
          formatter: (p: { data: [number, number, number] }) => {
            const [c, r, v] = p.data;
            const sign = v > 0 ? "+" : "";
            const label = v < 0 ? "负向影响" : v > 0 ? "正向影响" : "无显著影响";
            return `
              <div style="font-family:var(--font-sans);font-size:13px;line-height:1.5">
                <div style="color:${chartPalette.textTertiary};margin-bottom:4px">${matrix.rows[r]} · ${matrix.cols[c]}</div>
                <div style="color:${chartPalette.textPrimary};font-size:20px;font-weight:600;font-family:ui-monospace, 'JetBrains Mono', monospace">${sign}${v.toFixed(2)}</div>
                <div style="color:${chartPalette.textSecondary};margin-top:2px">${label}</div>
              </div>
            `;
          },
        },
        xAxis: {
          ...baseChartOption.xAxis,
          type: "category",
          data: matrix.cols,
          position: "top",
          axisLine: { show: false },
          axisLabel: {
            ...baseChartOption.xAxis.axisLabel,
            color: chartPalette.textSecondary,
            fontSize: 13,
            fontWeight: 500,
          },
          splitArea: { show: false },
        },
        yAxis: {
          ...baseChartOption.yAxis,
          type: "category",
          data: matrix.rows,
          inverse: true,
          axisLabel: {
            ...baseChartOption.yAxis.axisLabel,
            color: chartPalette.textSecondary,
            fontSize: 13,
            interval: 0,
          },
          splitArea: { show: false },
        },
        visualMap: {
          type: "continuous",
          min: -1,
          max: 1,
          dimension: 2,
          show: false,
          inRange: {
            color: [
              chartPalette.divergingNegative,
              chartPalette.divergingPaleNeg,
              chartPalette.divergingNeutral,
              chartPalette.divergingPalePos,
              chartPalette.divergingPositive,
            ],
          },
        },
        series: [
          {
            name: "影响",
            type: "heatmap",
            data,
            label: {
              show: true,
              color: chartPalette.textPrimary,
              fontSize: 13,
              fontFamily:
                'ui-monospace, "JetBrains Mono", "Sarasa Mono SC", Consolas, monospace',
              fontWeight: 600,
              textBorderColor: "#ffffff",
              textBorderWidth: 2,
              formatter: (p: { data: [number, number, number] }) => {
                const v = p.data[2];
                const sign = v > 0 ? "+" : "";
                return `${sign}${v.toFixed(2)}`;
              },
            },
            itemStyle: {
              borderColor: "#ffffff",
              borderWidth: 2,
              borderRadius: 3,
            },
            emphasis: {
              itemStyle: {
                borderColor: chartPalette.accent,
                borderWidth: 2,
                shadowBlur: 8,
                shadowColor: "rgba(47, 79, 182, 0.35)",
              },
              label: {
                fontSize: 14,
                fontWeight: 700,
              },
            },
            animationDelay: (i: number) => i * 20,
          },
        ],
      });

      chart.on("click", (params) => {
        const data = (params as { data?: unknown }).data;
        if (!Array.isArray(data) || data.length < 2) return;
        const c = data[0] as number;
        const r = data[1] as number;
        const ids = cellEvidence?.(matrix.rows[r], matrix.cols[c]) ?? [];
        if (ids.length) open(ids);
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
  }, [matrix, cellEvidence, open]);

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.chart} />
      <div className={styles.legend} aria-hidden="true">
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: chartPalette.divergingNegative }}
          />
          强负
        </span>
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{
              background: chartPalette.divergingNeutral,
              border: "1px solid var(--border-subtle)",
            }}
          />
          中性
        </span>
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: chartPalette.divergingPositive }}
          />
          强正
        </span>
      </div>
    </div>
  );
}
