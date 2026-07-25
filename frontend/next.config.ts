import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits .next/standalone — a self-contained server bundle with only
  // the node_modules files Next.js actually traced as used, instead of
  // requiring the whole node_modules tree at runtime. This is what lets
  // the Docker image's final stage skip `npm install` entirely and copy
  // just a few small directories — see frontend/Dockerfile's runner
  // stage for exactly what that saves.
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
