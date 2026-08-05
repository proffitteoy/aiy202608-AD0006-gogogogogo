import type { NextConfig } from "next";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1"],
  turbopack: { root: appRoot },
  // 关掉 Dev 模式左下角的 "N Issues" 悬浮徽章 — 路演时避免干扰
  devIndicators: false,
};

export default nextConfig;
