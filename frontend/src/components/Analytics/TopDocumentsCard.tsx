import { memo } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import topDocumentsData from "@/lib/mock-data/analytics-top-documents.json";

import type { TopDocument } from "./types";

const documents = topDocumentsData as TopDocument[];
const maxViews = Math.max(...documents.map((document) => document.views));

// Takes no props and renders the same static mock list every time, so it's
// memoized to skip re-rendering when a sibling's state changes (e.g. the
// page-level time range toggling) — nothing here depends on that.
export const TopDocumentsCard = memo(function TopDocumentsCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle level="h2">Top Knowledge Base Documents</CardTitle>
        <CardDescription>Most viewed, all time</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {documents.map((document, index) => (
          <div key={document.id} className="flex items-center gap-3">
            <span className="w-4 shrink-0 text-right text-xs font-medium text-muted-foreground">
              {index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm text-foreground">
                  {document.title}
                </p>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {document.views.toLocaleString()}
                </span>
              </div>
              <div
                className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted"
                aria-hidden="true"
              >
                <div
                  className="h-full rounded-full bg-info"
                  style={{ width: `${(document.views / maxViews) * 100}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
});
