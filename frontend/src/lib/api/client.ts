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

export interface UploadOptions {
  signal?: AbortSignal;
  onProgress?: (percent: number) => void;
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

  /**
   * Like post(), but returns the raw Response instead of a parsed body —
   * for endpoints that reply with a streamed body (e.g. text/event-stream)
   * rather than a single JSON payload. Reuses the same base URL, auth-token
   * request interceptor, and error/401 handling as request(); retries (via
   * the same retry config) only apply to the connection attempt itself —
   * once a response successfully starts streaming, retrying it would mean
   * replaying a request whose side effects (e.g. persisted chat history)
   * may have already partially happened, so callers reading the body must
   * handle a stream that drops partway through on their own.
   */
  async postStream(
    path: string,
    body?: unknown,
    options: ApiRequestOptions = {}
  ): Promise<Response> {
    const retryConfig = resolveRetryConfig(options.retry);
    let attempt = 0;

    for (;;) {
      try {
        return await this.executeStreamOnce(path, body, options);
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

  /**
   * Multipart file upload with progress — fetch() has no reliable
   * cross-browser upload-progress event, so this uses XMLHttpRequest
   * instead, but still reuses this client's base URL, auth-token request
   * interceptor, and error/401 handling. Retries (via the same retry
   * config as every other call) resend the whole file on a transient
   * network/5xx failure — safe here specifically because the backend's
   * upload handler only creates a document row after it has read the
   * FULL request body (see DocumentService.upload_document), so a
   * dropped or failed transfer never leaves a row behind to duplicate.
   */
  async upload<T>(
    path: string,
    formData: FormData,
    options: UploadOptions = {}
  ): Promise<T> {
    const retryConfig = resolveRetryConfig(options.retry);
    let attempt = 0;

    for (;;) {
      try {
        return await this.executeUploadOnce<T>(path, formData, options);
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

  // No DEFAULT_TIMEOUT_MS here, unlike executeOnce() — a streamed reply's
  // duration depends on how long the model takes to finish generating, not
  // a fixed request/response round trip, so only options.timeoutMs (if a
  // caller explicitly passes one) or options.signal bounds it.
  private async executeStreamOnce(
    path: string,
    body: unknown,
    options: ApiRequestOptions
  ): Promise<Response> {
    const headers = new Headers(options.headers);
    if (body !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    let signal = options.signal ?? new AbortController().signal;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    if (options.timeoutMs !== undefined) {
      const timeoutController = new AbortController();
      timeoutId = setTimeout(
        () =>
          timeoutController.abort(
            new DOMException("Request timed out", "TimeoutError")
          ),
        options.timeoutMs
      );
      signal = mergeSignals([options.signal, timeoutController.signal]);
    }

    try {
      const config = await this.requestInterceptors.run({
        url: this.buildUrl(path),
        method: "POST",
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal,
      });

      const response = await fetch(config.url, {
        method: config.method,
        headers: config.headers,
        body: config.body,
        signal: config.signal,
      });

      if (!response.ok) {
        throw await this.buildErrorFromResponse(response);
      }

      return response;
    } finally {
      if (timeoutId !== undefined) {
        clearTimeout(timeoutId);
      }
    }
  }

  // XHR, not fetch, is the executor here — deliberately, and only here —
  // specifically for xhr.upload.onprogress, which fetch has no equivalent
  // of. requestInterceptors still runs first so attachAuthToken's
  // Authorization header applies exactly like every other request; its
  // url/body/signal fields exist only to satisfy RequestConfig's shape and
  // are never used below (XHR takes the real FormData and abort wiring
  // separately, since it has no single fetch-style config object).
  private executeUploadOnce<T>(
    path: string,
    formData: FormData,
    options: UploadOptions
  ): Promise<T> {
    return this.requestInterceptors
      .run({
        url: this.buildUrl(path),
        method: "POST",
        headers: new Headers(),
        body: undefined,
        signal: options.signal ?? new AbortController().signal,
      })
      .then(
        (config) =>
          new Promise<T>((resolve, reject) => {
            if (options.signal?.aborted) {
              reject(new ApiError("Upload was cancelled.", { code: "ABORTED" }));
              return;
            }

            const xhr = new XMLHttpRequest();
            xhr.open("POST", config.url);

            config.headers.forEach((value, key) => {
              // FormData needs the browser's own auto-generated multipart
              // boundary in Content-Type — setting it manually would break
              // that, but attachAuthToken never sets one, so this only
              // ever strips a header this class didn't add anyway.
              if (key.toLowerCase() !== "content-type") {
                xhr.setRequestHeader(key, value);
              }
            });

            const handleAbort = () => xhr.abort();
            options.signal?.addEventListener("abort", handleAbort);
            const cleanup = () =>
              options.signal?.removeEventListener("abort", handleAbort);

            xhr.upload.onprogress = (event) => {
              if (event.lengthComputable) {
                options.onProgress?.(
                  Math.round((event.loaded / event.total) * 100)
                );
              }
            };

            xhr.onload = () => {
              cleanup();

              if (xhr.status >= 200 && xhr.status < 300) {
                if (xhr.status === 204 || !xhr.responseText) {
                  resolve(undefined as T);
                  return;
                }
                try {
                  resolve(JSON.parse(xhr.responseText) as T);
                } catch {
                  reject(
                    new ApiError(
                      "Received an invalid response from the server.",
                      { status: xhr.status, code: `HTTP_${xhr.status}` }
                    )
                  );
                }
                return;
              }

              let message =
                xhr.statusText || `Request failed with status ${xhr.status}`;
              let details: unknown;
              try {
                details = JSON.parse(xhr.responseText);
                if (
                  details &&
                  typeof details === "object" &&
                  "message" in details &&
                  typeof (details as { message: unknown }).message === "string"
                ) {
                  message = (details as { message: string }).message;
                }
              } catch {
                // Body wasn't valid JSON despite a non-2xx status — keep
                // the default message.
              }

              reject(
                new ApiError(message, {
                  status: xhr.status,
                  code: `HTTP_${xhr.status}`,
                  details,
                })
              );
            };

            xhr.onerror = () => {
              cleanup();
              reject(
                new ApiError("A network error occurred while uploading.", {
                  code: "NETWORK_ERROR",
                  isNetworkError: true,
                })
              );
            };

            xhr.onabort = () => {
              cleanup();
              reject(new ApiError("Upload was cancelled.", { code: "ABORTED" }));
            };

            xhr.send(formData);
          })
      );
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
