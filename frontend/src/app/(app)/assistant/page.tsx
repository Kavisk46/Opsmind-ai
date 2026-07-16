import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb";
import { AssistantConsole } from "@/components/Chat";
import { PageHeader } from "@/components/PageHeader";
import { getDefaultBreadcrumbItems } from "@/components/Sidebar/nav-items";

export const metadata: Metadata = {
  title: "AI Assistant",
};

export default function AssistantPage() {
  return (
    <>
      <Breadcrumb
        items={getDefaultBreadcrumbItems("/assistant")}
        className="mb-4"
      />
      <PageHeader
        title="AI Assistant"
        subtitle="Ask questions about your team's knowledge base"
      />
      <AssistantConsole />
    </>
  );
}
