import {
  BarChart3,
  Bot,
  FileText,
  LayoutDashboard,
  Search,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { BreadcrumbItem } from "@/components/Breadcrumb";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

export interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    id: "overview",
    label: "Overview",
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
      { label: "Analytics", href: "/analytics", icon: BarChart3 },
    ],
  },
  {
    id: "workspace",
    label: "Workspace",
    items: [
      { label: "Documents", href: "/documents", icon: FileText },
      { label: "AI Assistant", href: "/assistant", icon: Bot },
      { label: "Teams", href: "/teams", icon: Users },
    ],
  },
  {
    id: "tools",
    label: "Tools",
    items: [{ label: "Search", href: "/search", icon: Search }],
  },
];

export const footerNavItem: NavItem = {
  label: "Settings",
  href: "/settings",
  icon: Settings,
};

export function isNavItemActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function getActiveNavItem(pathname: string): NavItem | undefined {
  const allItems = [
    ...navGroups.flatMap((group) => group.items),
    footerNavItem,
  ];
  return allItems.find((item) => isNavItemActive(pathname, item.href));
}

// Sensible default trail for pages that don't need a custom one. Pages with
// dynamic entities (e.g. a document's own title) should build their own
// BreadcrumbItem[] instead of using this.
export function getDefaultBreadcrumbItems(pathname: string): BreadcrumbItem[] {
  const activeItem = getActiveNavItem(pathname);
  const items: BreadcrumbItem[] = [{ label: "Home", href: "/" }];

  if (activeItem && activeItem.href !== "/") {
    items.push({ label: activeItem.label });
  }

  return items;
}
