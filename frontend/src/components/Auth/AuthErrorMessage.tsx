interface AuthErrorMessageProps {
  message: string;
}

// Shared destructive error banner reused across every auth form.
export function AuthErrorMessage({ message }: AuthErrorMessageProps) {
  return (
    <p
      role="alert"
      className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {message}
    </p>
  );
}
