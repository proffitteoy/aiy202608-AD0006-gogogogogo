/**
 * ECharts 白底研报主题。
 *
 * 关键：ECharts / zrender 对 CSS Color 4（如 `oklch()`）的支持并不稳定，尤其是
 * 在 visualMap 做颜色插值时。为了保证 heatmap 一定能上色，这里所有颜色都写成
 * 十六进制/rgb（与 CSS 变量色值一一对应）。
 */

export const chartPalette = {
  bg: "transparent",
  gridLine: "#d5d7dc",
  textPrimary: "#232630",
  textSecondary: "#545963",
  textTertiary: "#83878f",

  viz: [
    "#2653c9", // 靛蓝
    "#a03cb5", // 紫罗兰
    "#b47a2e", // 沙金
    "#1d8480", // 青绿
    "#d13a48", // 珊瑚
    "#2f8659", // 森绿
    "#4238bb", // 深靛蓝
    "#6d7d24", // 橄榄
  ],

  risk: {
    high: "#c9302a",
    mid: "#b5842e",
    low: "#1e7d4d",
  },

  divergingNegative: "#d43a3f",
  divergingPaleNeg: "#f2b8b8",
  divergingNeutral: "#f4f5f7",
  divergingPalePos: "#b6dcc4",
  divergingPositive: "#1e7d4d",

  accent: "#2f4fb6",
};

export const baseChartOption = {
  textStyle: {
    fontFamily:
      'ui-monospace, "JetBrains Mono", "Sarasa Mono SC", Consolas, monospace',
    color: chartPalette.textSecondary,
  },
  grid: {
    top: 24,
    right: 16,
    bottom: 32,
    left: 44,
    containLabel: true,
  },
  tooltip: {
    backgroundColor: "#ffffff",
    borderColor: chartPalette.gridLine,
    borderWidth: 1,
    textStyle: {
      color: chartPalette.textPrimary,
      fontSize: 13,
    },
    extraCssText:
      "box-shadow: 0 8px 24px rgba(35, 38, 48, 0.12); border-radius: 4px;",
  },
  xAxis: {
    axisLine: { lineStyle: { color: chartPalette.gridLine } },
    axisTick: { show: false },
    axisLabel: { color: chartPalette.textTertiary, fontSize: 12 },
    splitLine: { show: false },
  },
  yAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: chartPalette.textTertiary, fontSize: 12 },
    splitLine: { lineStyle: { color: chartPalette.gridLine, type: "dashed" } },
  },
};
