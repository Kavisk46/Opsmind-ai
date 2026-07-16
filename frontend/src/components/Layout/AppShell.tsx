import { Suspense, type ReactNode } from "react";

import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { LoadingFallback } from "@/components/ui/loading-fallback";

import { RouteAnnouncer } from "./RouteAnnouncer";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <RouteAnnouncer />
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-(--z-toast) focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Navbar />
        <main id="main-content" className="flex-1 p-gutter">
          <div className="mx-auto w-full max-w-screen-2xl">
            <Suspense fallback={<LoadingFallback />}>{children}</Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}
