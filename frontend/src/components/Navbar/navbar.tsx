"use client";

import { Menu } from "lucide-react";
import Link from "next/link";

import { NotificationButton } from "@/components/NotificationButton";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserProfileDropdown } from "@/components/UserProfileDropdown";
import { useSidebarStore } from "@/store/sidebar-store";

export function Navbar() {
  const isSidebarOpen = useSidebarStore((state) => state.isOpen);
  const toggleSidebar = useSidebarStore((state) => state.toggle);

  return (
    <header className="sticky top-0 z-(--z-sticky) flex h-16 items-center gap-4 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/75 sm:px-6">
      <button
        type="button"
        onClick={toggleSidebar}
        aria-expanded={isSidebarOpen}
        aria-controls="app-sidebar"
        aria-label={isSidebarOpen ? "Close menu" : "Open menu"}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </button>

      <Link
        href="/"
        className="rounded-md text-lg font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
      >
        OpsMind AI
      </Link>

      <div className="flex-1" />

      <div className="flex items-center gap-1">
        <NotificationButton />
        <ThemeToggle />
        <UserProfileDropdown />
      </div>
    </header>
  );
}
