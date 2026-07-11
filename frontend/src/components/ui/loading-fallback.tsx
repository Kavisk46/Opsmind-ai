import { cn } from "@/lib/utils";

import { Spinner } from "./spinner";

interface LoadingFallbackProps {
  className?: string;
  label?: string;
  fullScreen?: boolean;
}

// The canonical <Suspense fallback> / route-loading component — use this
// instead of ad hoc spinner markup so loading states stay visually
// consistent across the app.
export function LoadingFallback({
  className,
  label = "Loading",
  fullScreen = false,
}: LoadingFallbackProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-center",
        fullScreen ? "min-h-screen" : "min-h-[240px]",
        className
      )}
    >
      <Spinner size="lg" label={label} />
    </div>
  );
}
