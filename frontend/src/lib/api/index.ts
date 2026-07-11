import { getEnvVar } from "@/lib/env";
import { logger } from "@/lib/logger";

import { ApiClient } from "./client";

export { ApiClient };
export type { ApiRequestOptions } from "./client";
export { ApiError, getFriendlyErrorMessage, normalizeError } from "./errors";
export { clearAuthToken, getAuthToken, setAuthToken } from "./token";
export type {
  ErrorInterceptor,
  RequestConfig,
  RequestInterceptor,
  ResponseInterceptor,
} from "./interceptors";
export type { RetryConfig } from "./retry";

export const apiClient = new ApiClient(
  getEnvVar("NEXT_PUBLIC_API_URL", "http://localhost:8000")
);

apiClient.useErrorInterceptor((error) => {
  logger.error(`API request failed: ${error.code ?? "UNKNOWN"}`, error, {
    status: error.status,
  });
  return error;
});
