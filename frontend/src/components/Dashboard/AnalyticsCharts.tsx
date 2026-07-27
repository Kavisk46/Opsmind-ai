import dynamic from "next/dynamic";

import { FadeIn } from "./FadeIn";

// Dynamically imported so recharts (and each chart's own bundle weight)
// loads in its own chunk instead of the Dashboard's main bundle.
const DocumentsChart = dynamic(() =>
  import("./DocumentsChart").then((mod) => mod.DocumentsChart)
);
const QueriesChart = dynamic(() =>
  import("./QueriesChart").then((mod) => mod.QueriesChart)
);
const EmbeddingsChart = dynamic(() =>
  import("./EmbeddingsChart").then((mod) => mod.EmbeddingsChart)
);
const StorageChart = dynamic(() =>
  import("./StorageChart").then((mod) => mod.StorageChart)
);

export function AnalyticsCharts() {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-foreground">
        Knowledge Analytics
      </h2>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <FadeIn>
          <DocumentsChart />
        </FadeIn>
        <FadeIn delay={0.05}>
          <QueriesChart />
        </FadeIn>
        <FadeIn delay={0.1}>
          <EmbeddingsChart />
        </FadeIn>
        <FadeIn delay={0.15}>
          <StorageChart />
        </FadeIn>
      </div>
    </div>
  );
}
