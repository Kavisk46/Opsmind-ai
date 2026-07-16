"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="Toggle theme"
      className={cn(
        "relative inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-all hover:bg-accent hover:text-accent-foreground active:scale-95",
        FOCUS_RING_CLASS
      )}
    >
      <Sun
        className="h-5 w-5 rotate-0 scale-100 transition-all duration-(--duration-slow) motion-reduce:transition-none dark:-rotate-90 dark:scale-0"
        aria-hidden="true"
      />
      <Moon
        className="absolute h-5 w-5 rotate-90 scale-0 transition-all duration-(--duration-slow) motion-reduce:transition-none dark:rotate-0 dark:scale-100"
        aria-hidden="true"
      />
    </button>
  );
}
