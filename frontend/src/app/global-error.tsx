"use client";

import { useEffect } from "react";

import { logger } from "@/lib/logger";

export default function GlobalError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    logger.error("Global error boundary caught an error", error, {
      digest: error.digest,
    });
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center bg-background text-foreground antialiased">
        <div className="flex flex-col items-center gap-4 p-8 text-center">
          <h2 className="text-lg font-semibold">Application error</h2>
          <p className="max-w-md text-sm text-muted-foreground">
            {error.message || "A critical error occurred. Please try again."}
          </p>
          <button
            type="button"
            onClick={() => unstable_retry()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
