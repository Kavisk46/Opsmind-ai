import { getEnvVar, isProd } from "@/lib/env";
import { logger } from "@/lib/logger";

import { ApiClient } from "./client";

export { ApiClient };
export type { ApiRequestOptions, UploadOptions } from "./client";
export { ApiError, getFriendlyErrorMessage, normalizeError } from "./errors";
export { clearAuthToken, getAuthToken, setAuthToken } from "./token";
export type {
  ErrorInterceptor,
  RequestConfig,
  RequestInterceptor,
  ResponseInterceptor,
} from "./interceptors";
export type { RetryConfig } from "./retry";

// The localhost fallback is only meant for local development. Module-level
// code runs during static generation, so this can't throw when the var is
// missing (that would fail the build for any page merely importing this
// module) — instead it logs loudly so a misconfigured production deploy is
// visible in server logs rather than silently pointing at localhost.
//
// process.env.NEXT_PUBLIC_API_URL is accessed here as a literal, static
// expression — REQUIRED for Next.js to inline it into the client bundle
// at build time (see lib/env.ts's getEnvVar doc comment for the exact
// bug this fixes: a dynamic `process.env[key]` lookup inside getEnvVar
// itself is invisible to that build-time pass and always evaluates to
// undefined in the browser, regardless of what's set in Vercel/Render).
const apiBaseUrl = getEnvVar(
  process.env.NEXT_PUBLIC_API_URL,
  "http://localhost:8000",
  "NEXT_PUBLIC_API_URL"
);

if (isProd && !process.env.NEXT_PUBLIC_API_URL) {
  logger.error(
    "NEXT_PUBLIC_API_URL is not set — this production build will call " +
      "http://localhost:8000, which will not work outside local development."
  );
}

export const apiClient = new ApiClient(apiBaseUrl);

apiClient.useErrorInterceptor((error) => {
  logger.error(`API request failed: ${error.code ?? "UNKNOWN"}`, error, {
    status: error.status,
  });
  return error;
});