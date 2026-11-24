import type { NextConfig } from "next";

const backend = process.env.ROADSECURE_BACKEND_URL || "http://127.0.0.1:8000";
const config: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` },
      { source: "/backend-health", destination: `${backend}/health` },
    ];
  },
};

export default config;
