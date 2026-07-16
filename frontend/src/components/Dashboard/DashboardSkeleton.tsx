import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function StatCardSkeleton() {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-4 pt-4 sm:p-6 sm:pt-6">
        <div className="min-w-0 flex-1 space-y-2">
          <Skeleton className="h-3.5 w-20" />
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-3.5 w-12" />
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

function ListCardSkeleton({ rows }: { rows: number }) {
  return (
    <Card>
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

// Reused loading state while Dashboard's mock data "loads" — mirrors the
// real layout's shape (hero, stat cards, chart cards, activity list) so the
// page doesn't jump around once data resolves, matching the sibling
// Settings/Analytics/KnowledgeBase pages that already do this.
export function DashboardSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading dashboard">
      <Card>
        <CardContent className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-64" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-9 w-36" />
            <Skeleton className="h-9 w-32" />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <StatCardSkeleton key={index} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCardSkeleton className="lg:col-span-2" />
        <ListCardSkeleton rows={3} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <ChartCardSkeleton key={index} />
        ))}
      </div>

      <ListCardSkeleton rows={5} />
    </div>
  );
}
