import type { LucideIcon } from "lucide-react";

interface SettingsEmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
}

// Shared empty-state body reused across the settings pages that render a
// list/table (domains, categories, keys, sessions, invoices, audit logs).
export function SettingsEmptyState({
  icon: Icon,
  title,
  description,
}: SettingsEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 py-12 text-center">
      {Icon && (
        <Icon className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      )}
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="max-w-xs text-xs text-muted-foreground">{description}</p>
    </div>
  );
}
