import { Bot, FileUp, FolderPlus, UserPlus, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface QuickAction {
  label: string;
  href: string;
  icon: LucideIcon;
}

// Hrefs point at real, existing routes — "Create Collection" has no
// dedicated page yet, so it lands on Documents (where collections are
// managed today) rather than a route this app can't actually serve.
const QUICK_ACTIONS: QuickAction[] = [
  { label: "Upload Document", href: "/documents", icon: FileUp },
  { label: "Ask AI", href: "/assistant", icon: Bot },
  { label: "Create Collection", href: "/documents", icon: FolderPlus },
  { label: "Invite Member", href: "/teams", icon: UserPlus },
];

interface QuickActionsProps {
  className?: string;
}

export function QuickActions({ className }: QuickActionsProps) {
  return (
    <div className={cn("grid grid-cols-2 gap-2 sm:flex sm:flex-wrap", className)}>
      {QUICK_ACTIONS.map((action) => (
        <Link
          key={action.label}
          href={action.href}
          className={cn(buttonVariants({ variant: "secondary" }), "justify-center")}
        >
          <action.icon className="h-4 w-4" aria-hidden="true" />
          {action.label}
        </Link>
      ))}
    </div>
  );
}
