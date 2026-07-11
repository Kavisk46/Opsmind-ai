export interface RetryConfig {
  retries: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  retries: 2,
  baseDelayMs: 300,
  maxDelayMs: 4000,
};

const RETRYABLE_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504]);

export function shouldRetry(
  attempt: number,
  config: RetryConfig,
  status?: number,
  isNetworkError?: boolean
): boolean {
  if (attempt >= config.retries) {
    return false;
  }
  if (isNetworkError) {
    return true;
  }
  return status !== undefined && RETRYABLE_STATUS_CODES.has(status);
}

export function getRetryDelay(attempt: number, config: RetryConfig): number {
  const exponential = config.baseDelayMs * 2 ** attempt;
  const capped = Math.min(exponential, config.maxDelayMs);
  const jitter = Math.random() * capped * 0.2;
  return capped + jitter;
}

export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
