export interface ApiErrorOptions {
  status?: number;
  code?: string;
  details?: unknown;
  isNetworkError?: boolean;
}

export class ApiError extends Error {
  readonly status?: number;
  readonly code?: string;
  readonly details?: unknown;
  readonly isNetworkError: boolean;

  constructor(message: string, options: ApiErrorOptions = {}) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.details = options.details;
    this.isNetworkError = options.isNetworkError ?? false;
  }
}

export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof DOMException && error.name === "AbortError") {
    return new ApiError("Request was aborted", { code: "ABORTED" });
  }

  if (error instanceof DOMException && error.name === "TimeoutError") {
    return new ApiError("Request timed out", {
      code: "TIMEOUT",
      isNetworkError: true,
    });
  }

  if (error instanceof Error) {
    return new ApiError(error.message, {
      code: "NETWORK_ERROR",
      isNetworkError: true,
    });
  }

  return new ApiError("An unknown error occurred", {
    code: "UNKNOWN_ERROR",
    details: error,
  });
}

const FRIENDLY_MESSAGES_BY_STATUS: Partial<Record<number, string>> = {
  400: "That request wasn't valid. Please check your input and try again.",
  401: "You need to sign in to continue.",
  403: "You don't have permission to do that.",
  404: "We couldn't find what you were looking for.",
  408: "That request timed out. Please try again.",
  409: "That conflicts with existing data.",
  422: "Some of the information provided isn't valid.",
  429: "You're doing that too much — please slow down and try again shortly.",
  500: "Something went wrong on our end. Please try again.",
  502: "Something went wrong on our end. Please try again.",
  503: "The service is temporarily unavailable. Please try again shortly.",
};

// `ApiError.message` is often a raw backend string not meant for display.
// Callers that need to show something to the user should use this instead.
export function getFriendlyErrorMessage(error: ApiError): string {
  if (error.isNetworkError && error.status === undefined) {
    return "Couldn't connect. Check your network connection and try again.";
  }

  if (error.status !== undefined && FRIENDLY_MESSAGES_BY_STATUS[error.status]) {
    return FRIENDLY_MESSAGES_BY_STATUS[error.status] as string;
  }

  return error.message || "Something went wrong. Please try again.";
}
