import { Sparkles } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { RouteAnnouncer } from "@/components/Layout";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

interface AuthLayoutProps {
  children: ReactNode;
}

// Deliberately chrome-free (no Sidebar/Navbar) — these routes are reached
// before a session exists, so the dashboard shell has nothing to show yet.
export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <RouteAnnouncer />
      <a
        href="#auth-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-(--z-toast) focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <header className="flex items-center justify-center py-8">
        <Link
          href="/"
          className={cn(
            "flex items-center gap-2 rounded-md text-lg font-semibold text-foreground",
            FOCUS_RING_CLASS
          )}
        >
          <Sparkles className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
          OpsMind AI
        </Link>
      </header>
      <main
        id="auth-content"
        className="flex flex-1 items-center justify-center px-4 pb-12"
      >
        <div className="w-full max-w-md">{children}</div>
      </main>
    </div>
  );
}
