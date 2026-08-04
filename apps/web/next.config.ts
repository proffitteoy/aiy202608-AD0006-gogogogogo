import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  transpilePackages: ["@xyflow/react", "@xyflow/system"],
};

export default nextConfig;
