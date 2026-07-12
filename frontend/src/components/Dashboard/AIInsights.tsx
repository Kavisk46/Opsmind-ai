import { InsightCard } from "@/components/Cards/InsightCard";
import type { BadgeProps } from "@/components/ui/badge";
import insightsData from "@/lib/mock-data/insights.json";

interface InsightEntry {
  id: string;
  title: string;
  description: string;
  category: string;
  confidence: number;
  actions: string[];
}

const insights = insightsData as InsightEntry[];

const CATEGORY_VARIANT: Record<string, BadgeProps["variant"]> = {
  Optimization: "info",
  Trend: "warning",
  Recommendation: "success",
};

export function AIInsights() {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-foreground">
        AI Insights
      </h2>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {insights.map((insight) => (
          <InsightCard
            key={insight.id}
            title={insight.title}
            description={insight.description}
            category={insight.category}
            categoryVariant={CATEGORY_VARIANT[insight.category] ?? "muted"}
            confidence={insight.confidence}
            actions={insight.actions}
          />
        ))}
      </div>
    </div>
  );
}
