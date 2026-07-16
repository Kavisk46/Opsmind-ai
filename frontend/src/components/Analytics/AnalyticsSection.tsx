import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface AnalyticsSectionProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}

// A titled, consistently-spaced container for a group of analytics widgets —
// mirrors the heading + grid pattern already used by the Dashboard's own
// Analytics/AI Insights sections. Deliberately NOT a Card itself: every
// widget it holds (StatCard, ChartCard, and similar) is already its own
// Card, so wrapping the section too would double-frame everything inside it.
export function AnalyticsSection({
  title,
  description,
  actions,
  className,
  children,
}: AnalyticsSectionProps) {
  return (
    <div className={cn(className)}>
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          {description && (
            <p className="mt-0.5 text-sm text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        )}
      </div>
      {children}
    </div>
  );
}
