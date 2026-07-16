"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import type { ReactNode } from "react";

import { isDev } from "@/lib/env";
import { getQueryClient } from "@/lib/query-client";

// Dynamically imported so the devtools module isn't pulled into the
// production client bundle at all, not just hidden behind isDev at render.
const ReactQueryDevtools = dynamic(() =>
  import("@tanstack/react-query-devtools").then((mod) => mod.ReactQueryDevtools)
);

interface QueryProviderProps {
  children: ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {isDev && (
        <ReactQueryDevtools
          initialIsOpen={false}
          buttonPosition="bottom-left"
        />
      )}
    </QueryClientProvider>
  );
}
