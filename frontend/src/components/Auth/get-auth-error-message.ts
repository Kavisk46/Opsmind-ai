// Shared fallback for turning a caught error into display text, reused
// across every auth form's catch block.
export function getAuthErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
