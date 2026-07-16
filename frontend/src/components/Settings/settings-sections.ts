import {
  Bell,
  Building2,
  CreditCard,
  Key,
  Palette,
  ScrollText,
  Shield,
  User,
  Users,
} from "lucide-react";

import type { SettingsSection } from "./types";

// Plain config, not JSON — mirrors Sidebar/nav-items.ts rather than the
// mock-data convention, since icons are components and this describes real
// navigation structure, not fake backend content.
export const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    id: "profile",
    label: "Profile",
    description: "Your personal information and public profile.",
    icon: User,
  },
  {
    id: "organization",
    label: "Organization",
    description: "Your company's identity and default workspace settings.",
    icon: Building2,
  },
  {
    id: "notifications",
    label: "Notifications",
    description: "Choose what you're notified about and how.",
    icon: Bell,
  },
  {
    id: "appearance",
    label: "Appearance",
    description: "Theme, density, and other display preferences.",
    icon: Palette,
  },
  {
    id: "apiKeys",
    label: "API Keys",
    description: "Manage keys used to authenticate API requests.",
    icon: Key,
  },
  {
    id: "security",
    label: "Security",
    description: "Password, two-factor authentication, and active sessions.",
    icon: Shield,
  },
  {
    id: "team",
    label: "Team",
    description: "Manage members, roles, and permissions.",
    icon: Users,
  },
  {
    id: "billing",
    label: "Billing",
    description: "Plan, payment method, and invoice history.",
    icon: CreditCard,
  },
  {
    id: "auditLogs",
    label: "Audit Logs",
    description: "A record of security-relevant actions on your account.",
    icon: ScrollText,
  },
];

export const DEFAULT_SETTINGS_SECTION_ID = SETTINGS_SECTIONS[0]?.id ?? "";
