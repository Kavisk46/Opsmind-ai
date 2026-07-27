import { StatCard } from "@/components/Cards/StatCard";
import { dashboardStats } from "@/lib/mock-data/mockDashboard";

import { FadeIn } from "./FadeIn";

export function StatsGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {dashboardStats.map((stat, index) => (
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
