"use client";

import { Area, AreaChart, Tooltip, XAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_AXIS_PROPS,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import aiStatusData from "@/lib/mock-data/ai-status.json";

interface QueryTrendPoint {
  day: string;
  queries: number;
}

interface AIStatusData {
  status: string;
  uptime: string;
  queryTrend: QueryTrendPoint[];
}

const data = aiStatusData as AIStatusData;

export function AIStatus() {
  return (
    <ChartCard
      title="AI Assistant Status"
      titleLevel="h2"
      description="Query volume over the last 7 days"
      className="lg:col-span-2"
      headerExtra={
        <div className="flex items-center gap-2 text-sm">
          <span
            className="h-2 w-2 shrink-0 rounded-full bg-success"
            aria-hidden="true"
          />
          <span className="font-medium text-foreground capitalize">
            {data.status}
          </span>
          <span className="text-muted-foreground">
            &middot; {data.uptime} uptime
          </span>
        </div>
      }
      chart={
        <AreaChart
          data={data.queryTrend}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="queryFill" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor={CHART_COLORS.primary}
                stopOpacity={0.3}
              />
              <stop
                offset="95%"
                stopColor={CHART_COLORS.primary}
                stopOpacity={0}
              />
            </linearGradient>
          </defs>
          <XAxis dataKey="day" {...CHART_AXIS_PROPS} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Area
            type="monotone"
            dataKey="queries"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            fill="url(#queryFill)"
          />
        </AreaChart>
      }
    >
      <AccessibleDataTable
        caption="AI query volume by day, last 7 days"
        columns={["Day", "Queries"]}
        rows={data.queryTrend.map((point) => [point.day, point.queries])}
      />
    </ChartCard>
  );
}
