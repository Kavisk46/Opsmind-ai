"use client";

import { BarChart3, Clock, FileText, Users } from "lucide-react";

import { useAiMetricsSummary } from "@/components/Analytics/analytics-api";
import { StatCard } from "@/components/Cards/StatCard";
import { useDocuments } from "@/components/KnowledgeBase/documents-api";
import { ApiError } from "@/lib/api";
import statsData from "@/lib/mock-data/stats.json";

interface StatEntry {
  id: string;
  label: string;
  value: string;
  change: number;
  isPositive: boolean;
}

// "Active Team Members" has no backend equivalent — this app has no
// team/organization/multi-user membership concept anywhere (GET /users
// lists every user platform-wide and is admin-only; it's not a per-team
// roster). Left on its original mock value rather than faked.
const membersFallback = (statsData as StatEntry[]).find(
  (stat) => stat.id === "members"
) as StatEntry;

export function StatsCards() {
  // Both hooks are plain useQuery() calls, cached and SHARED with
  // UploadModal.tsx / AnalyticsKpiCards.tsx via the same query keys — see
  // documents-api.ts / analytics-api.ts. Whichever component mounts
  // second gets an instant cache hit instead of a redundant request.
  const documentsQuery = useDocuments();
  const metricsQuery = useAiMetricsSummary();
  const isForbidden =
    metricsQuery.error instanceof ApiError && metricsQuery.error.status === 403;

  const documentsValue = documentsQuery.isPending
    ? "…"
    : documentsQuery.error
      ? "Unavailable"
      : documentsQuery.data.length.toLocaleString();

  // Same GET /internal/ai-metrics snapshot AnalyticsKpiCards.tsx uses —
  // admin-only (see analytics-api.ts), so a non-admin viewer sees these
  // two cards fall back to "Admin access required" rather than a
  // silently-faked number.
  const queriesValue = metricsQuery.isPending
    ? "…"
    : isForbidden
      ? "Admin access required"
      : metricsQuery.error
        ? "Unavailable"
        : metricsQuery.data.totalRequests.toLocaleString();

  const responseValue = metricsQuery.isPending
    ? "…"
    : isForbidden
      ? "Admin access required"
      : metricsQuery.error
        ? "Unavailable"
        : metricsQuery.data.avgLatencyMs !== null
          ? `${Math.round(metricsQuery.data.avgLatencyMs)}ms`
          : "No data yet";

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Documents Indexed"
        value={documentsValue}
        change={null}
        icon={FileText}
      />
      {/* Label corrected from the mock's "AI Queries Today" — the real
          metric behind this (see analytics-api.ts) is a bounded snapshot
          of at most the last 200 requests ever, not a daily count, so
          "Today" would misrepresent what the number actually means. */}
      <StatCard
        label="Total AI Queries"
        value={queriesValue}
        change={null}
        icon={BarChart3}
      />
      <StatCard
        label={membersFallback.label}
        value={membersFallback.value}
        change={membersFallback.change}
        isPositive={membersFallback.isPositive}
        icon={Users}
      />
      <StatCard
        label="Avg. Response Time"
        value={responseValue}
        change={null}
        icon={Clock}
      />
    </div>
  );
}
