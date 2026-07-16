import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb";
import { PageHeader } from "@/components/PageHeader";
import { Settings } from "@/components/Settings";
import { getDefaultBreadcrumbItems } from "@/components/Sidebar/nav-items";

export const metadata: Metadata = {
  title: "Settings",
};

export default function SettingsPage() {
  return (
    <>
      <Breadcrumb
        items={getDefaultBreadcrumbItems("/settings")}
        className="mb-4"
      />
      <PageHeader
        title="Settings"
        subtitle="Manage your account, workspace, and preferences"
      />
      <Settings />
    </>
  );
}
