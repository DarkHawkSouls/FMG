import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Only rewrite to local FastAPI server in development.
    // In production on Vercel, vercel.json routes to /api/index.py directly.
    if (process.env.NODE_ENV === "production" || process.env.VERCEL === "1") {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
