import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/format";

import { StatusBadge } from "./StatusBadge";
import type { QueryLogEntry } from "./types";

interface QueryLogTableProps {
  entries: QueryLogEntry[];
  isLoading?: boolean;
}

function formatTimestamp(value: string) {
  return formatDate(value, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function QueryLogTable({
  entries,
  isLoading = false,
}: QueryLogTableProps) {
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Loading query log"
        className="space-y-2 p-1"
      >
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-1 py-12 text-center">
        <p className="text-sm font-medium text-foreground">
          No queries found
        </p>
        <p className="max-w-xs text-xs text-muted-foreground">
          Try adjusting your filters or date range.
        </p>
      </div>
    );
  }

  return (
    <Table>
      <TableCaption>
        Recent AI queries, filtered by the controls above
      </TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>Timestamp</TableHead>
          <TableHead>User</TableHead>
          <TableHead>Category</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Response Time</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => (
          <TableRow key={entry.id}>
            <TableCell className="whitespace-nowrap text-muted-foreground">
              {formatTimestamp(entry.timestamp)}
            </TableCell>
            <TableCell className="whitespace-nowrap">{entry.user}</TableCell>
            <TableCell className="whitespace-nowrap">
              {entry.category}
            </TableCell>
            <TableCell>
              <StatusBadge status={entry.status} />
            </TableCell>
            <TableCell className="text-right whitespace-nowrap">
              {entry.responseMs.toLocaleString()}ms
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
