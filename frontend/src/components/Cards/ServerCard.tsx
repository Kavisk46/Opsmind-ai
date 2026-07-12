import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export type ServerStatusValue = "operational" | "degraded" | "down";

export interface ServerCardProps {
  name: string;
  status: ServerStatusValue;
  uptime: string;
}

const STATUS_VARIANT: Record<ServerStatusValue, BadgeProps["variant"]> = {
  operational: "success",
  degraded: "warning",
  down: "destructive",
};

const STATUS_LABEL: Record<ServerStatusValue, string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
};

export function ServerCard({ name, status, uptime }: ServerCardProps) {
  return (
    <Card>
      <CardContent className="p-4 pt-4 sm:p-4 sm:pt-4">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-medium text-foreground">{name}</p>
          <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">{uptime} uptime</p>
      </CardContent>
    </Card>
  );
}
