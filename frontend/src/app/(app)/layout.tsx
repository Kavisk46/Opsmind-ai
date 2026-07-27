import type { ReactNode } from "react";

import { RequireAuth } from "@/components/Auth";
import { AppShell } from "@/components/Layout";

interface AppGroupLayoutProps {
  children: ReactNode;
}

// RequireAuth is client-side defense in depth on top of proxy.ts's
// middleware-level protection (which already covers every route here) —
// see RequireAuth.tsx's own doc comment for why both layers exist.
export default function AppGroupLayout({ children }: AppGroupLayoutProps) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
