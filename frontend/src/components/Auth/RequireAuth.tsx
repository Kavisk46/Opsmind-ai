"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/components/Providers/AuthProvider";
import { LoadingFallback } from "@/components/ui/loading-fallback";

interface RequireAuthProps {
  children: ReactNode;
}

// Placeholder route guard — not yet applied to any existing page. Wrap a
// protected page's content in <RequireAuth> once real session persistence
// (vs. this in-memory mock) makes that meaningful.
export function RequireAuth({ children }: RequireAuthProps) {
  const router = useRouter();
  const { status } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status !== "authenticated") {
    return <LoadingFallback fullScreen />;
  }

  return <>{children}</>;
}
