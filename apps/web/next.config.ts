import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  // 关掉 Dev 模式左下角的 "N Issues" 悬浮徽章 — 路演时避免干扰
  devIndicators: false,
};

export default nextConfig;
