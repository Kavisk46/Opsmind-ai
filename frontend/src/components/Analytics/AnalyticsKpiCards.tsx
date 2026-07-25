"use client";

import { Activity, CheckCircle2, Clock, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { StatCard } from "@/components/Cards/StatCard";
import { normalizeError } from "@/lib/api";
import activeUsersData from "@/lib/mock-data/analytics-active-users.json";

import { getAiMetricsSummary, type AiMetricsSummary } from "./analytics-api";
import {
  average,
  percentChange,
  previousPeriodSlice,
  sliceByRange,
} from "./analytics-utils";
import type { ActiveUsersPoint, TimeRange } from "./types";

const activeUsers = activeUsersData as ActiveUsersPoint[];

interface AnalyticsKpiCardsProps {
  timeRange: TimeRange;
}

function roundedChange(current: number, previous: number): number {
  return Math.round(percentChange(current, previous) * 10) / 10;
}

type SummaryState =
  | { status: "loading" }
  | { status: "forbidden" }
  | { status: "error" }
  | { status: "ready"; summary: AiMetricsSummary };

// "Avg. Active Users" has no backend equivalent at all — this app has no
// session/user-activity tracking anywhere (verified: no such concept
// exists in AIMetricsService.summary() or anywhere else in the backend).
// Left on the same mock data/timeRange behavior as before; the other
// three cards below are real. See analytics-api.ts for why they're a
// flat admin-only snapshot rather than a time-series like this one.
export function AnalyticsKpiCards({ timeRange }: AnalyticsKpiCardsProps) {
  const [state, setState] = useState<SummaryState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    getAiMetricsSummary({ signal: controller.signal })
      .then((summary) => setState({ status: "ready", summary }))
      .catch((error) => {
        const apiError = normalizeError(error);
        if (apiError.code === "ABORTED") {
          return;
        }
        setState({ status: apiError.status === 403 ? "forbidden" : "error" });
      });

    return () => controller.abort();
  }, []);

  const currentUsers = sliceByRange(activeUsers, timeRange);
  const avgUsers = average(currentUsers.map((point) => point.users));
  const previousAvgUsers = average(
    previousPeriodSlice(activeUsers, timeRange).map((point) => point.users)
  );
  const usersChange = roundedChange(avgUsers, previousAvgUsers);

  const successRatePercent =
    state.status === "ready" && state.summary.totalRequests > 0
      ? (state.summary.successCount / state.summary.totalRequests) * 100
      : null;

  const cardsForState = (): {
    queriesValue: string;
    responseValue: string;
    successValue: string;
  } => {
    if (state.status === "forbidden") {
      return {
        queriesValue: "Admin access required",
        responseValue: "Admin access required",
        successValue: "Admin access required",
      };
    }
    if (state.status === "error") {
      return {
        queriesValue: "Unavailable",
        responseValue: "Unavailable",
        successValue: "Unavailable",
      };
    }
    if (state.status === "loading") {
      return { queriesValue: "…", responseValue: "…", successValue: "…" };
    }
    return {
      queriesValue: state.summary.totalRequests.toLocaleString(),
      responseValue:
        state.summary.avgLatencyMs !== null
          ? `${Math.round(state.summary.avgLatencyMs)}ms`
          : "No data yet",
      successValue:
        successRatePercent !== null ? `${successRatePercent.toFixed(1)}%` : "No data yet",
    };
  };

  const { queriesValue, responseValue, successValue } = cardsForState();

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* These three are a live, history-free snapshot (at most the last
          200 recorded requests — see analytics-api.ts) — there's no
          previous-period figure to compare against, so `change` is always
          null here rather than a fabricated percentage. */}
      <StatCard
        label="Total AI Queries"
        value={queriesValue}
        change={null}
        icon={Activity}
      />
      <StatCard
        label="Avg. Response Time"
        value={responseValue}
        change={null}
        icon={Clock}
      />
      <StatCard
        label="API Success Rate"
        value={successValue}
        change={null}
        icon={CheckCircle2}
      />
      <StatCard
        label="Avg. Active Users"
        value={Math.round(avgUsers).toLocaleString()}
        change={usersChange}
        isPositive={usersChange >= 0}
        icon={Users}
      />
    </div>
  );
}
