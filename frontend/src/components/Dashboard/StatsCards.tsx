"use client";

import { BarChart3, Clock, FileText, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { getAiMetricsSummary } from "@/components/Analytics/analytics-api";
import { StatCard } from "@/components/Cards/StatCard";
import { listDocuments } from "@/components/KnowledgeBase/documents-api";
import { normalizeError } from "@/lib/api";
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

type CardState =
  | { status: "loading" }
  | { status: "forbidden" }
  | { status: "error" }
  | { status: "ready"; value: string };

function valueForState(state: CardState): string {
  switch (state.status) {
    case "loading":
      return "…";
    case "forbidden":
      return "Admin access required";
    case "error":
      return "Unavailable";
    case "ready":
      return state.value;
  }
}

export function StatsCards() {
  const [documentsState, setDocumentsState] = useState<CardState>({
    status: "loading",
  });
  const [queriesState, setQueriesState] = useState<CardState>({
    status: "loading",
  });
  const [responseState, setResponseState] = useState<CardState>({
    status: "loading",
  });

  useEffect(() => {
    const controller = new AbortController();

    listDocuments({ signal: controller.signal })
      .then((documents) =>
        setDocumentsState({
          status: "ready",
          value: documents.length.toLocaleString(),
        })
      )
      .catch((error) => {
        if (normalizeError(error).code !== "ABORTED") {
          setDocumentsState({ status: "error" });
        }
      });

    // Same GET /internal/ai-metrics snapshot AnalyticsKpiCards.tsx uses —
    // admin-only (see analytics-api.ts), so a non-admin viewer will see
    // these two cards fall back to "Admin access required" rather than a
    // silently-faked number.
    getAiMetricsSummary({ signal: controller.signal })
      .then((summary) => {
        setQueriesState({
          status: "ready",
          value: summary.totalRequests.toLocaleString(),
        });
        setResponseState({
          status: "ready",
          value:
            summary.avgLatencyMs !== null
              ? `${Math.round(summary.avgLatencyMs)}ms`
              : "No data yet",
        });
      })
      .catch((error) => {
        const apiError = normalizeError(error);
        if (apiError.code === "ABORTED") {
          return;
        }
        const status = apiError.status === 403 ? "forbidden" : "error";
        setQueriesState({ status });
        setResponseState({ status });
      });

    return () => controller.abort();
  }, []);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Documents Indexed"
        value={valueForState(documentsState)}
        change={null}
        icon={FileText}
      />
      {/* Label corrected from the mock's "AI Queries Today" — the real
          metric behind this (see analytics-api.ts) is a bounded snapshot
          of at most the last 200 requests ever, not a daily count, so
          "Today" would misrepresent what the number actually means. */}
      <StatCard
        label="Total AI Queries"
        value={valueForState(queriesState)}
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
        value={valueForState(responseState)}
        change={null}
        icon={Clock}
      />
    </div>
  );
}
