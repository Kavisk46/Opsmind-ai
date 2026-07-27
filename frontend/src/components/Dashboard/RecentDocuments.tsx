import { FileText, MoreHorizontal } from "lucide-react";
import Link from "next/link";

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
import { formatDate } from "@/lib/format";
import {
  recentDocuments,
  type DocumentStatus,
} from "@/lib/mock-data/mockDashboard";
import { cn } from "@/lib/utils";

import { FadeIn } from "./FadeIn";

const STATUS_VARIANT: Record<DocumentStatus, BadgeProps["variant"]> = {
  ready: "success",
  embedding: "info",
  processing: "warning",
  failed: "destructive",
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  ready: "Ready",
  embedding: "Embedding",
  processing: "Processing",
  failed: "Failed",
};

interface RecentDocumentsProps {
  className?: string;
}

export function RecentDocuments({ className }: RecentDocumentsProps) {
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

        {recentDocuments.length === 0 ? (
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
              {recentDocuments.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell className="max-w-64">
                    <div className="flex items-center gap-2.5">
                      <FileText
                        className="h-4 w-4 shrink-0 text-muted-foreground"
                        aria-hidden="true"
                      />
                      <span className="truncate font-medium">{doc.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {doc.owner}
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[doc.status]}>
                      {STATUS_LABEL[doc.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {doc.sizeLabel}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatDate(doc.uploadedAt)}
                  </TableCell>
                  <TableCell className="text-right">
                    <button
                      type="button"
                      className={cn(
                        buttonVariants({ variant: "ghost", size: "icon" }),
                        "h-8 w-8"
                      )}
                      aria-label={`Actions for ${doc.name}`}
                    >
                      <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                    </button>
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
