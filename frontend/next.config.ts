import type { NextConfig } from "next";

const staticExport = process.env.MA_DARWIN_STATIC_EXPORT === "1";

const nextConfig: NextConfig = staticExport
  ? {
      output: "export",
      trailingSlash: true,
      images: { unoptimized: true },
    }
  : {
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
