import { TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface StatCardProps {
  label: string;
  value: string;
  // null means "no period-over-period comparison is available" (e.g. a
  // backend snapshot with no history behind it) — renders a neutral note
  // instead of a fabricated percentage. Existing callers passing a real
  // number are unaffected.
  change: number | null;
  isPositive?: boolean;
  icon: LucideIcon;
  /** Optional third line of context below the trend (e.g. "12 active in the last hour"). */
  description?: string;
}

export function StatCard({
  label,
  value,
  change,
  isPositive = true,
  icon: Icon,
  description,
}: StatCardProps) {
  const isIncrease = change !== null && change >= 0;
  const TrendIcon = isIncrease ? TrendingUp : TrendingDown;

  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-4 pt-4 sm:p-6 sm:pt-6">
        <div className="min-w-0">
          <p className="truncate text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
            {value}
          </p>
          {change === null ? (
            <p className="mt-2 text-xs font-medium text-muted-foreground">
              No comparison data available
            </p>
          ) : (
            <div
              className={cn(
                "mt-2 inline-flex items-center gap-1 text-xs font-medium",
                isPositive ? "text-success" : "text-destructive"
              )}
            >
              <TrendIcon className="h-3.5 w-3.5" aria-hidden="true" />
              <span>
                {isIncrease ? "+" : ""}
                {change}%
              </span>
              <span className="sr-only">
                {isPositive ? "improvement" : "decline"} vs. last period
              </span>
            </div>
          )}
          {description && (
            <p className="mt-2 truncate text-xs text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </CardContent>
    </Card>
  );
}
