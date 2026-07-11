"use client";

import { Suspense, type ReactNode } from "react";

import { LoadingFallback } from "@/components/ui/loading-fallback";

import { AuthProvider } from "./AuthProvider";
import { ErrorBoundary } from "./ErrorBoundary";
import { QueryProvider } from "./QueryProvider";
import { ThemeProvider } from "./ThemeProvider";
import { ToastProvider } from "./ToastProvider";

interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <ErrorBoundary>
        <QueryProvider>
          <AuthProvider>
            <Suspense fallback={<LoadingFallback fullScreen />}>
              {children}
            </Suspense>
            <ToastProvider />
          </AuthProvider>
        </QueryProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}
