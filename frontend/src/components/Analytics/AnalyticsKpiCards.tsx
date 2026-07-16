import { Activity, CheckCircle2, Clock, Users } from "lucide-react";

import { StatCard } from "@/components/Cards/StatCard";
import activeUsersData from "@/lib/mock-data/analytics-active-users.json";
import apiRequestsData from "@/lib/mock-data/analytics-api-requests.json";
import queryVolumeData from "@/lib/mock-data/analytics-query-volume.json";
import responseTimeData from "@/lib/mock-data/analytics-response-time.json";

import {
  average,
  percentChange,
  previousPeriodSlice,
  sliceByRange,
  sum,
} from "./analytics-utils";
import type {
  ActiveUsersPoint,
  ApiRequestPoint,
  QueryVolumePoint,
  ResponseTimePoint,
  TimeRange,
} from "./types";

const queryVolume = queryVolumeData as QueryVolumePoint[];
const apiRequests = apiRequestsData as ApiRequestPoint[];
const responseTime = responseTimeData as ResponseTimePoint[];
const activeUsers = activeUsersData as ActiveUsersPoint[];

interface AnalyticsKpiCardsProps {
  timeRange: TimeRange;
}

function successRatePercent(points: ApiRequestPoint[]): number {
  const totalSuccess = sum(points.map((point) => point.success));
  const totalError = sum(points.map((point) => point.error));
  const total = totalSuccess + totalError;
  return total === 0 ? 0 : (totalSuccess / total) * 100;
}

function roundedChange(current: number, previous: number): number {
  return Math.round(percentChange(current, previous) * 10) / 10;
}

export function AnalyticsKpiCards({ timeRange }: AnalyticsKpiCardsProps) {
  const currentQueries = sliceByRange(queryVolume, timeRange);
  const totalQueries = sum(currentQueries.map((point) => point.queries));
  const previousTotalQueries = sum(
    previousPeriodSlice(queryVolume, timeRange).map((point) => point.queries)
  );
  const queriesChange = roundedChange(totalQueries, previousTotalQueries);

  const currentResponse = sliceByRange(responseTime, timeRange);
  const avgResponseMs = average(currentResponse.map((point) => point.avgMs));
  const previousAvgResponseMs = average(
    previousPeriodSlice(responseTime, timeRange).map((point) => point.avgMs)
  );
  const responseChange = roundedChange(avgResponseMs, previousAvgResponseMs);

  const currentApi = sliceByRange(apiRequests, timeRange);
  const currentSuccessRate = successRatePercent(currentApi);
  const previousSuccessRate = successRatePercent(
    previousPeriodSlice(apiRequests, timeRange)
  );
  const successRateChange = roundedChange(
    currentSuccessRate,
    previousSuccessRate
  );

  const currentUsers = sliceByRange(activeUsers, timeRange);
  const avgUsers = average(currentUsers.map((point) => point.users));
  const previousAvgUsers = average(
    previousPeriodSlice(activeUsers, timeRange).map((point) => point.users)
  );
  const usersChange = roundedChange(avgUsers, previousAvgUsers);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Total AI Queries"
        value={totalQueries.toLocaleString()}
        change={queriesChange}
        isPositive={queriesChange >= 0}
        icon={Activity}
      />
      <StatCard
        label="Avg. Response Time"
        value={`${Math.round(avgResponseMs)}ms`}
        change={responseChange}
        isPositive={responseChange <= 0}
        icon={Clock}
      />
      <StatCard
        label="API Success Rate"
        value={`${currentSuccessRate.toFixed(1)}%`}
        change={successRateChange}
        isPositive={successRateChange >= 0}
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
