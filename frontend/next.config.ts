import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow local and LAN origins in development to prevent HMR blocks
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.1.181"],

  // Proxy API requests directly to FastAPI backend on port 8000
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
      {
        source: "/ws/transit/:path*",
        destination: "http://127.0.0.1:8000/ws/transit/:path*",
      },
      {
        source: "/ws",
        destination: "http://127.0.0.1:8000/ws",
      },
    ];
  },
};

export default nextConfig;
