import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function StatCardSkeleton() {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-4 pt-4 sm:p-6 sm:pt-6">
        <div className="min-w-0 flex-1 space-y-2">
          <Skeleton className="h-3.5 w-20" />
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-3.5 w-24" />
        </div>
        <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
      </CardContent>
    </Card>
  );
}

function ChartCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-56" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-48 w-full" />
      </CardContent>
    </Card>
  );
}

function ListCardSkeleton({ rows, className }: { rows: number; className?: string }) {
  return (
    <Card className={className}>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-56" />
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
            <div className="min-w-0 flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-3/4" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function HealthCardSkeleton() {
  return (
    <Card>
      <CardContent className="space-y-3 p-4 pt-4 sm:p-4 sm:pt-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-2.5 w-2.5 rounded-full" />
        </div>
        <Skeleton className="h-3 w-full" />
      </CardContent>
    </Card>
  );
}

// Mirrors the real Dashboard's layout (header, stat grid, insights, recent
// lists, timeline, charts, health, quick access) so the page doesn't jump
// around once the simulated load finishes.
export function DashboardSkeleton() {
  return (
    <div className="space-y-8" role="status" aria-label="Loading dashboard">
      <Card>
        <CardContent className="flex flex-col gap-6 p-6 sm:p-8">
          <div className="flex items-start gap-3">
            <Skeleton className="mt-1 h-6 w-6 shrink-0 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-7 w-48" />
              <Skeleton className="h-4 w-40" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:flex">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-9 w-full sm:w-36" />
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <StatCardSkeleton key={index} />
        ))}
      </div>

      <ChartCardSkeleton />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <ListCardSkeleton rows={4} className="xl:col-span-2" />
        <ListCardSkeleton rows={4} />
      </div>

      <ListCardSkeleton rows={5} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <ChartCardSkeleton key={index} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <HealthCardSkeleton key={index} />
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton key={index} className="h-24 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}
