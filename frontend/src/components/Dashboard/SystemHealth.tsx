import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import systemHealthData from "@/lib/mock-data/system-health.json";

interface HealthMetric {
  id: string;
  label: string;
  value: number;
}

const metrics = systemHealthData as HealthMetric[];

export function SystemHealth() {
  return (
    <Card>
      <CardHeader>
        <CardTitle level="h2">System Health</CardTitle>
        <CardDescription>Current resource utilization</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {metrics.map((metric) => (
          <div key={metric.id}>
            <div className="mb-1.5 flex items-center justify-between text-sm">
              <span className="text-foreground">{metric.label}</span>
              <span className="text-muted-foreground">{metric.value}%</span>
            </div>
            <Progress value={metric.value} label={metric.label} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
