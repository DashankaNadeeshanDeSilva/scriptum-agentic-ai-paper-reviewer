import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" for Docker (Node.js server), "export" for pip package (static HTML)
  // Set NEXT_OUTPUT=export when building for pip distribution
  output: (process.env.NEXT_OUTPUT as "standalone" | "export") || "standalone",
};

export default nextConfig;
