import type {
  FieldError,
  FieldPath,
  FieldValues,
  UseFormSetError,
} from "react-hook-form";

import { normalizeError } from "@/lib/api";

export function getFieldErrorMessage(
  error: FieldError | undefined
): string | undefined {
  return error?.message;
}

interface ServerFieldErrors {
  [field: string]: string | string[];
}

// Assumes the backend returns field-level validation failures as
// `{ errors: { fieldName: "message" | ["message", ...] } }` inside the
// response body (surfaced here as ApiError.details). Adjust this if the
// actual backend contract differs.
function extractFieldErrors(details: unknown): ServerFieldErrors | undefined {
  if (!details || typeof details !== "object") {
    return undefined;
  }
  const { errors } = details as { errors?: unknown };
  if (!errors || typeof errors !== "object") {
    return undefined;
  }
  return errors as ServerFieldErrors;
}

export function applyServerErrors<T extends FieldValues>(
  setError: UseFormSetError<T>,
  error: unknown
): void {
  const apiError = normalizeError(error);
  const fieldErrors = extractFieldErrors(apiError.details);

  if (fieldErrors) {
    for (const [field, messages] of Object.entries(fieldErrors)) {
      const message = Array.isArray(messages) ? messages[0] : messages;
      if (message) {
        setError(field as FieldPath<T>, { type: "server", message });
      }
    }
    return;
  }

  setError("root", { type: "server", message: apiError.message });
}
