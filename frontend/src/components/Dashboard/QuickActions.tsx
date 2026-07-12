import {
  BarChart3,
  Bot,
  FileUp,
  UserPlus,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface QuickAction {
  label: string;
  href: string;
  icon: LucideIcon;
}

const QUICK_ACTIONS: QuickAction[] = [
  { label: "Upload Document", href: "/documents", icon: FileUp },
  { label: "Ask AI Assistant", href: "/assistant", icon: Bot },
  { label: "Invite Teammate", href: "/teams", icon: UserPlus },
  { label: "View Analytics", href: "/analytics", icon: BarChart3 },
];

export function QuickActions() {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-foreground">
        Quick Actions
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {QUICK_ACTIONS.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className={cn(
              buttonVariants({ variant: "outline" }),
              "h-auto flex-col gap-2 py-4"
            )}
          >
            <action.icon className="h-5 w-5 text-primary" aria-hidden="true" />
            <span>{action.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
