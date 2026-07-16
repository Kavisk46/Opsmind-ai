"use client";

import { Download, ScrollText } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import { formatDate } from "@/lib/format";
import auditLogsData from "@/lib/mock-data/admin-audit-logs.json";
import { toast } from "@/lib/toast";

import { AdminStatusBadge } from "./AdminStatusBadge";
import { SettingsEmptyState } from "./SettingsEmptyState";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";

interface AuditLogEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  target: string;
  status: "success" | "failed";
}

const entries = auditLogsData as AuditLogEntry[];

function formatTimestamp(value: string) {
  return formatDate(value, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function AuditLogsSettings() {
  const isLoading = useSimulatedLoad();

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle level="h2">Audit Logs</CardTitle>
          <CardDescription>
            A record of security-relevant actions on your account.
          </CardDescription>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => toast("Log export isn't available in this preview.")}
          className="shrink-0 gap-1.5"
        >
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          Export
        </Button>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <SettingsEmptyState
            icon={ScrollText}
            title="No activity yet"
            description="Actions taken on your account will show up here."
          />
        ) : (
          <Table>
            <TableCaption>Recent account activity</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatTimestamp(entry.timestamp)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-foreground">
                    {entry.actor}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {entry.action}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {entry.target}
                  </TableCell>
                  <TableCell>
                    <AdminStatusBadge
                      label={entry.status === "success" ? "Success" : "Failed"}
                      variant={entry.status === "success" ? "success" : "destructive"}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
