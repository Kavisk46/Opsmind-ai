import {
  BarChart3,
  Clock,
  FileText,
  Users,
  type LucideIcon,
} from "lucide-react";

import { StatCard } from "@/components/Cards/StatCard";
import statsData from "@/lib/mock-data/stats.json";

interface StatEntry {
  id: string;
  label: string;
  value: string;
  change: number;
  isPositive: boolean;
}

const ICONS_BY_ID: Record<string, LucideIcon> = {
  documents: FileText,
  queries: BarChart3,
  members: Users,
  response: Clock,
};

const stats = statsData as StatEntry[];

export function StatsCards() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <StatCard
          key={stat.id}
          label={stat.label}
          value={stat.value}
          change={stat.change}
          isPositive={stat.isPositive}
          icon={ICONS_BY_ID[stat.id] ?? BarChart3}
        />
      ))}
    </div>
  );
}
