import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const badgeVariants = cva(
  "inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        success: "bg-success/15 text-success",
        warning: "bg-warning/15 text-warning",
        info: "bg-info/15 text-info",
        destructive: "bg-destructive/15 text-destructive",
        muted: "bg-muted text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "muted",
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
