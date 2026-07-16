import type { Metadata } from "next";

import { Dashboard } from "@/components/Dashboard";
import { PageHeader } from "@/components/PageHeader";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function Home() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Enterprise Knowledge Intelligence Platform"
      />
      <Dashboard />
    </>
  );
}
