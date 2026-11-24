import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL?.replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Standalone mode is only for self-hosted Docker containers.
  // Never enable on Vercel, as it conflicts with Vercel's internal NFT file tracing.
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" } : {}),
  ...(backendUrl
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: `${backendUrl}/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
