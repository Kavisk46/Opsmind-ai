"use client";

import { StatCard } from "@/components/Cards/StatCard";
import { useDocumentStats } from "@/components/KnowledgeBase/documents-api";
import { formatFileSize, formatNumber } from "@/lib/format";
import { dashboardStats } from "@/lib/mock-data/mockDashboard";

import { FadeIn } from "./FadeIn";

// "Documents" and "Storage Used" come from the real GET /documents/stats
// endpoint; the other six (conversations, chunks, embeddings, users,
// collections, AI requests) stay on mockDashboard.ts — this backend has
// no endpoints for those yet (verified: no matching routes anywhere in
// api/routes/), so faking a live connection for them would be dishonest
// in the other direction. `change: null` for the two real cards rather
// than a fabricated percentage — GET /documents/stats has no
// period-over-period comparison to report, and StatCard already has a
// real "No comparison data available" state for exactly this case.
export function StatsGrid() {
  const statsQuery = useDocumentStats();

  const stats = dashboardStats.map((stat) => {
    if (stat.id === "documents") {
      return {
        ...stat,
        value: statsQuery.data
          ? formatNumber(statsQuery.data.totalDocuments)
          : "…",
        change: null,
        description: statsQuery.data
          ? `${Object.keys(statsQuery.data.documentsByType).length} file types`
          : "Loading…",
      };
    }
    if (stat.id === "storage") {
      return {
        ...stat,
        value: statsQuery.data
          ? formatFileSize(statsQuery.data.totalStorageBytes)
          : "…",
        change: null,
        description: "Live usage",
      };
    }
    return stat;
  });

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, index) => (
        <FadeIn key={stat.id} delay={index * 0.04}>
          <StatCard
            label={stat.label}
            value={stat.value}
            change={stat.change}
            isPositive={stat.trend === "up"}
            icon={stat.icon}
            description={stat.description}
          />
        </FadeIn>
      ))}
    </div>
  );
}
