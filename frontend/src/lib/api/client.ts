import { ApiError, normalizeError } from "./errors";
import {
  InterceptorManager,
  type ErrorInterceptor,
  type RequestConfig,
  type RequestInterceptor,
  type ResponseInterceptor,
} from "./interceptors";
import {
  DEFAULT_RETRY_CONFIG,
  getRetryDelay,
  shouldRetry,
  wait,
  type RetryConfig,
} from "./retry";
import { getAuthToken } from "./token";

const DEFAULT_TIMEOUT_MS = 15000;

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface ApiRequestOptions {
  headers?: HeadersInit;
  signal?: AbortSignal;
  timeoutMs?: number;
  retry?: boolean | Partial<RetryConfig>;
}

function resolveRetryConfig(retry: ApiRequestOptions["retry"]): RetryConfig {
  if (retry === false) {
    return { ...DEFAULT_RETRY_CONFIG, retries: 0 };
  }
  if (retry === true || retry === undefined) {
    return DEFAULT_RETRY_CONFIG;
  }
  return { ...DEFAULT_RETRY_CONFIG, ...retry };
}

function mergeSignals(signals: Array<AbortSignal | undefined>): AbortSignal {
  const controller = new AbortController();

  for (const signal of signals) {
    if (!signal) continue;
    if (signal.aborted) {
      controller.abort(signal.reason);
      break;
    }
    signal.addEventListener("abort", () => controller.abort(signal.reason), {
      once: true,
    });
  }

  return controller.signal;
}

const attachAuthToken: RequestInterceptor = (config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
};

export class ApiClient {
  private readonly baseUrl: string;
  private readonly requestInterceptors =
    new InterceptorManager<RequestConfig>();
  private readonly responseInterceptors = new InterceptorManager<Response>();
  private readonly errorInterceptors = new InterceptorManager<ApiError>();
  private unauthorizedHandler?: () => void;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.requestInterceptors.use(attachAuthToken);
  }

  useRequestInterceptor(interceptor: RequestInterceptor): number {
    return this.requestInterceptors.use(interceptor);
  }

  ejectRequestInterceptor(id: number): void {
    this.requestInterceptors.eject(id);
  }

  useResponseInterceptor(interceptor: ResponseInterceptor): number {
    return this.responseInterceptors.use(interceptor);
  }

  ejectResponseInterceptor(id: number): void {
    this.responseInterceptors.eject(id);
  }

  useErrorInterceptor(interceptor: ErrorInterceptor): number {
    return this.errorInterceptors.use(interceptor);
  }

  ejectErrorInterceptor(id: number): void {
    this.errorInterceptors.eject(id);
  }

  /** Called after a request ultimately fails with a 401, once interceptors have run. */
  onUnauthorized(handler: () => void): void {
    this.unauthorizedHandler = handler;
  }

  get<T>(path: string, options?: ApiRequestOptions): Promise<T> {
    return this.request<T>("GET", path, undefined, options);
  }

  post<T>(
    path: string,
    body?: unknown,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.request<T>("POST", path, body, options);
  }

  put<T>(
    path: string,
    body?: unknown,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.request<T>("PUT", path, body, options);
  }

  patch<T>(
    path: string,
    body?: unknown,
    options?: ApiRequestOptions
  ): Promise<T> {
    return this.request<T>("PATCH", path, body, options);
  }

  delete<T>(path: string, options?: ApiRequestOptions): Promise<T> {
    return this.request<T>("DELETE", path, undefined, options);
  }

  private async request<T>(
    method: HttpMethod,
    path: string,
    body: unknown,
    options: ApiRequestOptions = {}
  ): Promise<T> {
    const retryConfig = resolveRetryConfig(options.retry);
    let attempt = 0;

    for (;;) {
      try {
        return await this.executeOnce<T>(method, path, body, options);
      } catch (error) {
        const apiError = normalizeError(error);

        if (
          !shouldRetry(
            attempt,
            retryConfig,
            apiError.status,
            apiError.isNetworkError
          )
        ) {
          const finalError = await this.errorInterceptors.run(apiError);
          if (finalError.status === 401) {
            this.unauthorizedHandler?.();
          }
          throw finalError;
        }

        await wait(getRetryDelay(attempt, retryConfig));
        attempt += 1;
      }
    }
  }

  private async executeOnce<T>(
    method: HttpMethod,
    path: string,
    body: unknown,
    options: ApiRequestOptions
  ): Promise<T> {
    const headers = new Headers(options.headers);
    if (body !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const timeoutController = new AbortController();
    const timeoutId = setTimeout(
      () =>
        timeoutController.abort(
          new DOMException("Request timed out", "TimeoutError")
        ),
      options.timeoutMs ?? DEFAULT_TIMEOUT_MS
    );

    try {
      const config = await this.requestInterceptors.run({
        url: this.buildUrl(path),
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: mergeSignals([options.signal, timeoutController.signal]),
      });

      const rawResponse = await fetch(config.url, {
        method: config.method,
        headers: config.headers,
        body: config.body,
        signal: config.signal,
      });

      const response = await this.responseInterceptors.run(rawResponse);

      if (!response.ok) {
        throw await this.buildErrorFromResponse(response);
      }

      return await this.parseResponse<T>(response);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private buildUrl(path: string): string {
    if (/^https?:\/\//.test(path)) {
      return path;
    }
    return `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
  }

  private isJsonResponse(response: Response): boolean {
    return (response.headers.get("content-type") ?? "").includes(
      "application/json"
    );
  }

  private async buildErrorFromResponse(response: Response): Promise<ApiError> {
    let message =
      response.statusText || `Request failed with status ${response.status}`;
    let details: unknown;

    if (this.isJsonResponse(response)) {
      try {
        details = await response.json();
        if (
          details &&
          typeof details === "object" &&
          "message" in details &&
          typeof (details as { message: unknown }).message === "string"
        ) {
          message = (details as { message: string }).message;
        }
      } catch {
        // Body wasn't valid JSON despite the content-type — keep the default message.
      }
    }

    return new ApiError(message, {
      status: response.status,
      code: `HTTP_${response.status}`,
      details,
    });
  }

  private async parseResponse<T>(response: Response): Promise<T> {
    if (
      response.status === 204 ||
      response.headers.get("content-length") === "0"
    ) {
      return undefined as T;
    }

    if (this.isJsonResponse(response)) {
      return (await response.json()) as T;
    }

    return (await response.text()) as unknown as T;
  }
}
