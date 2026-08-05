import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

/**
 * 骨架阶段用系统字体后备链（PingFang SC / Georgia / Consolas），构建不依赖 Google Fonts。
 * Demo 若要更强编辑气质，可用 next/font/local 挂本地 Source Serif 4 + Inter woff2。
 */

export const metadata: Metadata = {
  title: "RiskTrace | 事件·情绪·传导 可追溯研究平台",
  description:
    "从突发事件到风险判断，每一步都能追回原始证据的研究工作台。",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
