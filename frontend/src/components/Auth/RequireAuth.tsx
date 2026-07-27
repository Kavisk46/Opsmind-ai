"use client";
/* eslint-disable no-console -- temporary debug instrumentation, remove after diagnosis */

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/components/Providers/AuthProvider";
import { LoadingFallback } from "@/components/ui/loading-fallback";

interface RequireAuthProps {
  children: ReactNode;
}

// Client-side defense in depth for every route under app/(app) — see
// that group's layout.tsx, which wraps its children in this component.
// proxy.ts (middleware) is the primary gate and runs first, on every
// request; this is a SECOND, independent check against the same
// AuthProvider state every page already reads, for the same reason
// real APIs enforce auth server-side even though a UI also hides
// buttons a user can't use — a client-side router guard is exactly as
// bypassable as any other client code, so it's a UX backstop layered on
// top of proxy.ts, never a replacement for the backend's own
// get_current_user check on every actual data request.
export function RequireAuth({ children }: RequireAuthProps) {
  const router = useRouter();
  const { status, user } = useAuth();

  console.log("REQUIRE AUTH RENDER", { status, user });

  useEffect(() => {
    if (status === "unauthenticated") {
      console.log("REDIRECTING TO LOGIN");
      router.replace("/login");
    }
  }, [status, router]);

  if (status !== "authenticated") {
    return <LoadingFallback fullScreen />;
  }

  return <>{children}</>;
}
