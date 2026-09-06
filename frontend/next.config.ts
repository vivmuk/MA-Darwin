import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const upstream = process.env.API_UPSTREAM;
    if (!upstream) return [];
    const base = upstream.replace(/\/$/, "");
    return [
      { source: "/api/:path*", destination: `${base}/:path*` },
      { source: "/upstream/:path*", destination: `${base}/:path*` },
    ];
  },
};

export default nextConfig;
