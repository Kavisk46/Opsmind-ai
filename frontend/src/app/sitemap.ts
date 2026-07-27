import type { MetadataRoute } from "next";

import { getEnvVar } from "@/lib/env";

// Placeholder sitemap — almost every route requires authentication and
// isn't meaningful to index (see robots.ts); this covers the public entry
// points only. Extend with real content routes if/when this app grows a
// public marketing surface.
export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = getEnvVar(
    process.env.NEXT_PUBLIC_APP_URL,
    "http://localhost:3000",
    "NEXT_PUBLIC_APP_URL"
  );
  const lastModified = new Date();

  return [
    { url: baseUrl, lastModified },
    { url: `${baseUrl}/login`, lastModified },
    { url: `${baseUrl}/signup`, lastModified },
  ];
}
