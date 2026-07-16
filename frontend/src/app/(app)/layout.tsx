import type { ReactNode } from "react";

import { AppShell } from "@/components/Layout";

interface AppGroupLayoutProps {
  children: ReactNode;
}

export default function AppGroupLayout({ children }: AppGroupLayoutProps) {
  return <AppShell>{children}</AppShell>;
}
