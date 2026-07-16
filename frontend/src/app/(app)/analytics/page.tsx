import type { Metadata } from "next";

import { Analytics } from "@/components/Analytics";
import { Breadcrumb } from "@/components/Breadcrumb";
import { PageHeader } from "@/components/PageHeader";
import { getDefaultBreadcrumbItems } from "@/components/Sidebar/nav-items";

export const metadata: Metadata = {
  title: "Analytics",
};

export default function AnalyticsPage() {
  return (
    <>
      <Breadcrumb
        items={getDefaultBreadcrumbItems("/analytics")}
        className="mb-4"
      />
      <PageHeader
        title="Analytics"
        subtitle="Usage, performance, and engagement trends across the platform"
      />
      <Analytics />
    </>
  );
}
