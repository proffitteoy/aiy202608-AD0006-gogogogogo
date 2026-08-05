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

/* =========================================================
 * Dark 变体 —— 用于 data-theme="dark" 作用域内的图表
 * 提亮 viz 调色板、翻转文字色、网格线加深加透明
 * ========================================================= */
export const darkChartPalette = {
  bg: "transparent",
  gridLine: "#2a2d33",
  textPrimary: "#f0f1f3",
  textSecondary: "#c0c3c8",
  textTertiary: "#83878f",

  viz: [
    "#5a86e6", // 亮靛蓝
    "#c46be0", // 亮紫罗兰
    "#e0a750", // 亮沙金
    "#4ab8b0", // 亮青绿
    "#f06a76", // 亮珊瑚
    "#5cb677", // 亮森绿
    "#7c72ea", // 亮深靛
    "#a8b74a", // 亮橄榄
  ],

  risk: {
    high: "#ff7a70",
    mid: "#f0c060",
    low: "#7fd08f",
  },

  divergingNegative: "#ff7a70",
  divergingPaleNeg: "#5a3540",
  divergingNeutral: "#2a2d33",
  divergingPalePos: "#2f5040",
  divergingPositive: "#7fd08f",

  accent: "#5a86e6",
};

export const baseDarkChartOption = {
  textStyle: {
    fontFamily:
      'ui-monospace, "JetBrains Mono", "Sarasa Mono SC", Consolas, monospace',
    color: darkChartPalette.textSecondary,
  },
  grid: {
    top: 24,
    right: 16,
    bottom: 32,
    left: 44,
    containLabel: true,
  },
  tooltip: {
    backgroundColor: "#1a1d24",
    borderColor: darkChartPalette.gridLine,
    borderWidth: 1,
    textStyle: {
      color: darkChartPalette.textPrimary,
      fontSize: 13,
    },
    extraCssText:
      "box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5); border-radius: 4px;",
  },
  xAxis: {
    axisLine: { lineStyle: { color: darkChartPalette.gridLine } },
    axisTick: { show: false },
    axisLabel: { color: darkChartPalette.textTertiary, fontSize: 12 },
    splitLine: { show: false },
  },
  yAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: darkChartPalette.textTertiary, fontSize: 12 },
    splitLine: {
      lineStyle: { color: darkChartPalette.gridLine, type: "dashed" },
    },
  },
};
