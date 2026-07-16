import type { ReactElement, ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ChartCardProps {
  title: string;
  /** Forwarded to CardTitle — see its own doc comment. Defaults to h3. */
  titleLevel?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
  description?: string;
  headerExtra?: ReactNode;
  className?: string;
  /** The Recharts chart element — passed as ResponsiveContainer's single child. */
  chart: ReactElement;
  /** Extra content rendered below the chart (e.g. an AccessibleDataTable). */
  children?: ReactNode;
}

export function ChartCard({
  title,
  titleLevel,
  description,
  headerExtra,
  className,
  chart,
  children,
}: ChartCardProps) {
  return (
    <Card className={cn(className)}>
      <CardHeader
        className={cn(headerExtra && "flex-row items-start justify-between")}
      >
        <div>
          <CardTitle level={titleLevel}>{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>
        {headerExtra}
      </CardHeader>
      <CardContent>
        <div className="h-64" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            {chart}
          </ResponsiveContainer>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}
