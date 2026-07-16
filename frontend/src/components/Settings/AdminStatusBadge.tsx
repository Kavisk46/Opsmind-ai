import { Badge, type BadgeProps } from "@/components/ui/badge";

interface AdminStatusBadgeProps {
  label: string;
  variant: BadgeProps["variant"];
}

// Generic status → Badge renderer shared by API Keys, Billing, and Audit
// Logs — each page supplies its own status-to-variant mapping (the status
// vocabularies differ per domain), this just renders the result
// consistently.
export function AdminStatusBadge({ label, variant }: AdminStatusBadgeProps) {
  return <Badge variant={variant}>{label}</Badge>;
}
