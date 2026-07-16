import { memo } from "react";

import { Card, CardContent } from "@/components/ui/card";

import { ApiKeysSettings } from "./ApiKeysSettings";
import { AppearanceSettings } from "./AppearanceSettings";
import { AuditLogsSettings } from "./AuditLogsSettings";
import { BillingSettings } from "./BillingSettings";
import { NotificationsSettings } from "./NotificationsSettings";
import { OrganizationSettings } from "./OrganizationSettings";
import { ProfileSettings } from "./ProfileSettings";
import { SecuritySettings } from "./SecuritySettings";
import type { SettingsSection } from "./types";

interface SettingsContentProps {
  section: SettingsSection;
}

// Routes to a real page for the sections built out so far; anything else
// (currently just Team) still falls back to the placeholder body below.
// Memoized so toggling the mobile nav (which doesn't change `section`) doesn't
// re-render the active page underneath it.
export const SettingsContent = memo(function SettingsContent({
  section,
}: SettingsContentProps) {
  switch (section.id) {
    case "profile":
      return <ProfileSettings />;
    case "organization":
      return <OrganizationSettings />;
    case "appearance":
      return <AppearanceSettings />;
    case "notifications":
      return <NotificationsSettings />;
    case "apiKeys":
      return <ApiKeysSettings />;
    case "security":
      return <SecuritySettings />;
    case "billing":
      return <BillingSettings />;
    case "auditLogs":
      return <AuditLogsSettings />;
    default:
      return <SettingsPlaceholder section={section} />;
  }
});

function SettingsPlaceholder({ section }: SettingsContentProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <section.icon className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-foreground">
            {section.label}
          </h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            {section.description}
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          This section is coming soon.
        </p>
      </CardContent>
    </Card>
  );
}
