import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Shared surface for floating dropdown/popover panels (notifications,
// account menu, etc.) — positioning (absolute/right/mt/width) stays local
// to each consumer since that varies per trigger.
export const POPOVER_PANEL_CLASS =
  "z-(--z-popover) animate-scale-in rounded-lg border border-border bg-popover text-popover-foreground shadow-popover motion-reduce:animate-none";
