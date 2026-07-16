import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb";
import { KnowledgeBase, UploadButton } from "@/components/KnowledgeBase";
import { PageHeader } from "@/components/PageHeader";
import { getDefaultBreadcrumbItems } from "@/components/Sidebar/nav-items";

export const metadata: Metadata = {
  title: "Documents",
};

export default function DocumentsPage() {
  return (
    <>
      <Breadcrumb
        items={getDefaultBreadcrumbItems("/documents")}
        className="mb-4"
      />
      <PageHeader
        title="Documents"
        subtitle="Your team's knowledge base — search, organize, and manage every file in one place"
        actions={<UploadButton />}
      />
      <KnowledgeBase />
    </>
  );
}
