import { Card, CardContent } from "@/components/ui/card";
import { healthEntries, type HealthStatus } from "@/lib/mock-data/mockDashboard";
import { cn } from "@/lib/utils";

import { FadeIn } from "./FadeIn";

const STATUS_DOT_CLASS: Record<HealthStatus, string> = {
  operational: "bg-success",
  degraded: "bg-warning",
  down: "bg-destructive",
};

const STATUS_LABEL: Record<HealthStatus, string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
};

export function HealthCards() {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-foreground">
        System Health
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {healthEntries.map((entry, index) => (
          <FadeIn key={entry.id} delay={index * 0.04}>
            <Card>
              <CardContent className="p-4 pt-4 sm:p-4 sm:pt-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <entry.icon
                      className="h-4 w-4 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <p className="text-sm font-medium text-foreground">
                      {entry.label}
                    </p>
                  </div>
                  <span className="relative flex h-2.5 w-2.5 shrink-0">
                    {entry.status !== "operational" && (
                      <span
                        className={cn(
                          "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
                          STATUS_DOT_CLASS[entry.status]
                        )}
                        aria-hidden="true"
                      />
                    )}
                    <span
                      className={cn(
                        "relative inline-flex h-2.5 w-2.5 rounded-full",
                        STATUS_DOT_CLASS[entry.status]
                      )}
                      aria-hidden="true"
                    />
                  </span>
                </div>
                <p className="mt-2 text-xs font-medium text-muted-foreground">
                  {STATUS_LABEL[entry.status]}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {entry.description}
                </p>
              </CardContent>
            </Card>
          </FadeIn>
        ))}
      </div>
    </div>
  );
}
