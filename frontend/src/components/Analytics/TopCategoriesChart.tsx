"use client";

import { Bar, BarChart, LabelList, Tooltip, XAxis, YAxis } from "recharts";

import {
  AccessibleDataTable,
  CHART_COLORS,
  CHART_TOOLTIP_STYLE,
  ChartCard,
} from "@/components/Charts";
import categoriesData from "@/lib/mock-data/analytics-query-categories.json";

import type { CategoryBreakdown } from "./types";

// Ranked by magnitude, not identity — per the data-viz method, a part-to-whole
// breakdown with long category names is a horizontal bar (ranked, direct
// labels), not a pie: a single sequential hue reads more clearly here than a
// multi-color categorical palette would.
const data = [...(categoriesData as CategoryBreakdown[])].sort(
  (a, b) => b.value - a.value
);

const Y_AXIS_WIDTH = 110;
const MAX_LABEL_LENGTH = 14;

// A fixed axis width wide enough for "Security & Compliance" would leave
// almost no room for the bars themselves on a narrow phone. Truncating
// keeps the axis compact on every viewport — the full name is still
// available via the tooltip and the sr-only data table below.
function truncateLabel(value: unknown) {
  if (typeof value !== "string") {
    return "";
  }
  return value.length > MAX_LABEL_LENGTH
    ? `${value.slice(0, MAX_LABEL_LENGTH - 1)}…`
    : value;
}

export function TopCategoriesChart() {
  return (
    <ChartCard
      title="Queries by Category"
      description="Share of total AI queries, all time"
      chart={
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 24, left: 8, bottom: 0 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="category"
            width={Y_AXIS_WIDTH}
            tickFormatter={truncateLabel}
            stroke="var(--color-muted-foreground)"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={false} />
          <Bar dataKey="value" fill={CHART_COLORS.info} radius={[0, 4, 4, 0]}>
            <LabelList
              dataKey="value"
              position="right"
              style={{ fill: "var(--color-muted-foreground)", fontSize: 12 }}
            />
          </Bar>
        </BarChart>
      }
    >
      <AccessibleDataTable
        caption="AI queries by category, all time"
        columns={["Category", "Queries"]}
        rows={data.map((point) => [point.category, point.value])}
      />
    </ChartCard>
  );
}
