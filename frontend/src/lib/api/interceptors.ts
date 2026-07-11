import type { ApiError } from "./errors";

export interface RequestConfig {
  url: string;
  method: string;
  headers: Headers;
  body?: BodyInit;
  signal: AbortSignal;
}

export type RequestInterceptor = (
  config: RequestConfig
) => RequestConfig | Promise<RequestConfig>;

// Interceptors that need to read the response body must call response.clone()
// first — the body stream can only be consumed once.
export type ResponseInterceptor = (
  response: Response
) => Response | Promise<Response>;

export type ErrorInterceptor = (
  error: ApiError
) => ApiError | Promise<ApiError>;

export class InterceptorManager<T> {
  private handlers: Array<{ id: number; fn: (value: T) => T | Promise<T> }> =
    [];
  private nextId = 0;

  use(fn: (value: T) => T | Promise<T>): number {
    const id = this.nextId++;
    this.handlers.push({ id, fn });
    return id;
  }

  eject(id: number): void {
    this.handlers = this.handlers.filter((handler) => handler.id !== id);
  }

  async run(value: T): Promise<T> {
    let result = value;
    for (const { fn } of this.handlers) {
      result = await fn(result);
    }
    return result;
  }
}
