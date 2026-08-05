import type { EventSummary, PlatformPulse } from "@/lib/types";

/**
 * 首页 mock 数据。sparkline 是 24 点数组，代表过去 24h 热度采样。
 */

export const pulse: PlatformPulse = {
  activeEvents: 128,
  highRiskEvents: 17,
  pendingReview: 5,
  heatWave: [
    12, 15, 14, 18, 22, 28, 32, 40, 55, 62, 58, 71, 84, 96, 108, 92, 78, 66, 54,
    47, 38, 30, 22, 18,
  ],
};

export const events: EventSummary[] = [
  {
    id: "evt_001",
    title: "某上市公司公告造假疑云",
    risk: "high",
    publishedAt: "2026-08-04T07:07:00Z",
    sourceCount: 47,
    authoritativeSourceCount: 4,
    heatChangePercent: 342,
    sparkline: [
      8, 10, 12, 14, 18, 22, 30, 45, 68, 82, 96, 108, 120, 132, 128, 115, 102,
      92, 84, 78, 74, 71, 68, 66,
    ],
    sentiment: -0.72,
    diversity: 0.68,
    reviewed: { done: 1, total: 3 },
    freshness: { updatedAt: "2026-08-04T07:20:12Z", staleMinutes: 2 },
  },
  {
    id: "evt_002",
    title: "XX 行业监管新规征求意见",
    risk: "mid",
    publishedAt: "2026-08-04T05:32:00Z",
    sourceCount: 23,
    authoritativeSourceCount: 6,
    heatChangePercent: 58,
    sparkline: [
      14, 16, 15, 18, 20, 22, 24, 25, 28, 30, 32, 34, 38, 42, 44, 45, 43, 40,
      38, 36, 34, 32, 30, 28,
    ],
    sentiment: 0.12,
    diversity: 0.82,
    reviewed: { done: 0, total: 2 },
  },
  {
    id: "evt_003",
    title: "境外大宗商品价格异动引发关注",
    risk: "mid",
    publishedAt: "2026-08-04T03:14:00Z",
    sourceCount: 18,
    authoritativeSourceCount: 3,
    heatChangePercent: -12,
    sparkline: [
      45, 44, 42, 40, 38, 36, 35, 34, 32, 30, 28, 27, 26, 25, 24, 24, 23, 22,
      22, 21, 20, 20, 19, 19,
    ],
    sentiment: -0.28,
    diversity: 0.55,
    reviewed: { done: 2, total: 2 },
  },
  {
    id: "evt_004",
    title: "某新兴市场资金流出加速",
    risk: "low",
    publishedAt: "2026-08-04T02:11:00Z",
    sourceCount: 11,
    authoritativeSourceCount: 2,
    heatChangePercent: 8,
    sparkline: [
      6, 6, 7, 7, 8, 8, 9, 9, 9, 10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 12,
      13, 13, 13,
    ],
    sentiment: -0.08,
    diversity: 0.44,
    reviewed: { done: 1, total: 1 },
  },
  {
    id: "evt_005",
    title: "科技板块财报季展望偏乐观",
    risk: "low",
    publishedAt: "2026-08-03T22:45:00Z",
    sourceCount: 9,
    authoritativeSourceCount: 3,
    heatChangePercent: -3,
    sparkline: [
      10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 11, 11, 11, 11, 10, 10, 10,
      10, 10, 9, 9, 9, 9,
    ],
    sentiment: 0.34,
    diversity: 0.6,
    reviewed: { done: 0, total: 1 },
  },
];
