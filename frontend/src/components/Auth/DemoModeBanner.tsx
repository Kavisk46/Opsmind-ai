"use client";

import { X } from "lucide-react";
import { useState } from "react";

import { useAuth } from "@/components/Providers/AuthProvider";
import { getSessionStorageItem, setSessionStorageItem } from "@/lib/storage";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

const DISMISSED_KEY = "opsmind:demo-banner-dismissed";

// Shown only while a Portfolio Demo Mode session is active (see
// AuthProvider's `isGuest`, set by loginAsGuest()). Dismissal is
// remembered via sessionStorage rather than localStorage, so it clears
// itself the next time someone starts a fresh guest session in a new tab,
// per the "does not reappear during the same session" requirement.
export function DemoModeBanner() {
  const { isGuest } = useAuth();
  const [isDismissed, setIsDismissed] = useState(() =>
    getSessionStorageItem(DISMISSED_KEY, false)
  );

  if (!isGuest || isDismissed) {
    return null;
  }

  const handleDismiss = () => {
    setSessionStorageItem(DISMISSED_KEY, true);
    setIsDismissed(true);
  };

  return (
    <div
      role="region"
      aria-label="Portfolio demo notice"
      className="flex items-start gap-3 border-b border-border bg-info/10 px-4 py-3 sm:items-center sm:px-6"
    >
      <div className="min-w-0 flex-1 text-sm">
        <p className="font-medium text-info">Portfolio Demo</p>
        <p className="text-muted-foreground">
          You are exploring the frontend demonstration of OpsMind AI.
          Authentication and backend services are intentionally mocked for
          portfolio purposes.
        </p>
      </div>
      <button
        type="button"
        onClick={handleDismiss}
        aria-label="Dismiss portfolio demo banner"
        className={cn(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
          FOCUS_RING_CLASS
        )}
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
