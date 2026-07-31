"use client";

import { FileText, MoreHorizontal } from "lucide-react";
import Link from "next/link";

import { useDocumentStats } from "@/components/KnowledgeBase/documents-api";
import { useAuth } from "@/components/Providers/AuthProvider";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getFriendlyErrorMessage, normalizeError } from "@/lib/api";
import { formatDate, formatFileSize } from "@/lib/format";
import { cn } from "@/lib/utils";

import { FadeIn } from "./FadeIn";

// Real backend document statuses (models/document.py's DocumentStatus
// enum) — "uploaded" was missing from this map before real data existed
// since the mock fixture never produced that value.
const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  uploaded: "info",
  processing: "warning",
  embedding: "info",
  ready: "success",
  failed: "destructive",
};

const STATUS_LABEL: Record<string, string> = {
  uploaded: "Uploaded",
  processing: "Processing",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

interface RecentDocumentsProps {
  className?: string;
}

export function RecentDocuments({ className }: RecentDocumentsProps) {
  const { user } = useAuth();
  const statsQuery = useDocumentStats();
  const recentUploads = statsQuery.data?.recentUploads ?? [];

  return (
    <FadeIn className={className}>
      <Card className="flex h-full flex-col">
        <CardHeader className="flex-row items-start justify-between">
          <div>
            <CardTitle level="h2">Recent Documents</CardTitle>
            <CardDescription>Latest uploads across your workspace</CardDescription>
          </div>
          <Link
            href="/documents"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
          >
            View all
          </Link>
        </CardHeader>

        {statsQuery.isPending ? (
          <p className="px-4 pb-6 text-sm text-muted-foreground sm:px-6">
            Loading documents…
          </p>
        ) : statsQuery.error ? (
          <div className="px-4 pb-6 sm:px-6">
            <EmptyState
              icon={FileText}
              title="Couldn't load documents"
              description={getFriendlyErrorMessage(normalizeError(statsQuery.error))}
            />
          </div>
        ) : recentUploads.length === 0 ? (
          <div className="px-4 pb-6 sm:px-6">
            <EmptyState
              icon={FileText}
              title="No documents yet"
              description="Upload your first document to start building your knowledge base."
            />
          </div>
        ) : (
          <Table>
            <TableCaption>Recently uploaded documents and their processing status</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead>Document</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentUploads.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell className="max-w-64">
                    <div className="flex items-center gap-2.5">
                      <FileText
                        className="h-4 w-4 shrink-0 text-muted-foreground"
                        aria-hidden="true"
                      />
                      <span className="truncate font-medium">{doc.filename}</span>
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {user?.name ?? "You"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[doc.status] ?? "muted"}>
                      {STATUS_LABEL[doc.status] ?? doc.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatFileSize(doc.sizeBytes)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatDate(doc.createdAt)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      href="/documents"
                      className={cn(
                        buttonVariants({ variant: "ghost", size: "icon" }),
                        "h-8 w-8"
                      )}
                      aria-label={`Open ${doc.filename} in Documents`}
                    >
                      <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </FadeIn>
  );
}
