import { AlertTriangle, CheckCircle2, Clock, type LucideIcon } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";

import type { QueryLogStatus } from "./types";

const STATUS_CONFIG: Record<
  QueryLogStatus,
  { label: string; variant: BadgeProps["variant"]; icon: LucideIcon }
> = {
  success: { label: "Success", variant: "success", icon: CheckCircle2 },
  error: { label: "Error", variant: "destructive", icon: AlertTriangle },
  timeout: { label: "Timeout", variant: "warning", icon: Clock },
};

interface StatusBadgeProps {
  status: QueryLogStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, variant, icon: Icon } = STATUS_CONFIG[status];

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" aria-hidden="true" />
      {label}
    </Badge>
  );
}
