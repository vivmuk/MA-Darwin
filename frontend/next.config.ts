import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const upstream = process.env.API_UPSTREAM;
    if (!upstream) return [];
    return [{ source: "/upstream/:path*", destination: `${upstream}/:path*` }];
  },
};

export default nextConfig;
