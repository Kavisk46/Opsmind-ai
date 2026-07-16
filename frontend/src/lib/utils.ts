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

// Standard keyboard-focus ring, applied directly to interactive elements
// that don't go through the shared Button component (raw buttons, links,
// inputs, custom widgets).
export const FOCUS_RING_CLASS =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

// Standard row inside a POPOVER_PANEL_CLASS panel (dropdown options, filter
// items) — layout plus the hover/transition treatment shared by every
// select-style popover menu. Pair with FOCUS_RING_CLASS for keyboard focus.
export const POPOVER_ITEM_CLASS =
  "flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-sm transition-colors hover:bg-accent";
