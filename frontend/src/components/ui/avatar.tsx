import { UserCircle } from "lucide-react";

import { cn } from "@/lib/utils";

interface AvatarProps {
  name?: string;
  size?: number;
  className?: string;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase();
}

// Decorative by design — the accessible name for "whose avatar this is"
// comes from surrounding text or the trigger's own aria-label, not from here.
export function Avatar({ name, size = 32, className }: AvatarProps) {
  const initials = name ? getInitials(name) : "";

  return (
    <span
      style={{ width: size, height: size }}
      className={cn(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-accent text-accent-foreground",
        className
      )}
      aria-hidden="true"
    >
      {initials ? (
        <span className="text-xs font-medium">{initials}</span>
      ) : (
        <UserCircle className="h-full w-full text-muted-foreground" />
      )}
    </span>
  );
}
