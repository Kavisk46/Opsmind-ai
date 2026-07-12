import { Dashboard } from "@/components/Dashboard";
import { PageHeader } from "@/components/PageHeader";

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
