import type { MetadataRoute } from "next";

import { getEnvVar } from "@/lib/env";

// Everything under (app) requires an authenticated session and redirects
// to /login otherwise — not meaningful for indexing, so it's excluded
// alongside the API route. The (auth) pages (login, signup, etc.) are the
// genuinely public surface and stay crawlable.
export default function robots(): MetadataRoute.Robots {
  const baseUrl = getEnvVar("NEXT_PUBLIC_APP_URL", "http://localhost:3000");

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/assistant", "/documents", "/analytics", "/settings"],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
