"use client";

import { LogOut, Settings } from "lucide-react";
import Link from "next/link";
import { useId } from "react";

import { useAuth } from "@/components/Providers";
import { footerNavItem } from "@/components/Sidebar/nav-items";
import { Avatar } from "@/components/ui/avatar";
import { useDisclosure } from "@/hooks/use-disclosure";
import { toast } from "@/lib/toast";
import { cn, POPOVER_PANEL_CLASS } from "@/lib/utils";

export function UserProfileDropdown() {
  const { user, status, logout } = useAuth();
  const { isOpen, toggle, close, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();

  const isAuthenticated = status === "authenticated" && user !== null;
  const name = isAuthenticated ? user.name : "Guest";
  const email = isAuthenticated ? user.email : "Not signed in";

  const handleLogout = async () => {
    await logout();
    close();
    toast("Signed out.");
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={`Account menu for ${name}`}
        className="flex items-center gap-2 rounded-md px-1.5 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Avatar name={isAuthenticated ? user.name : undefined} />
        <span className="hidden sm:inline">{name}</span>
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="region"
          aria-label="Account"
          className={cn(
            POPOVER_PANEL_CLASS,
            "absolute right-0 mt-2 w-64 max-w-[calc(100vw-2rem)] p-1.5"
          )}
        >
          <div className="flex items-center gap-3 rounded-md px-2.5 py-2">
            <Avatar name={isAuthenticated ? user.name : undefined} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">
                {name}
              </p>
              <p className="truncate text-xs text-muted-foreground">{email}</p>
            </div>
          </div>

          <div className="my-1 h-px bg-border" role="separator" />

          <Link
            href={footerNavItem.href}
            onClick={close}
            className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Settings
              className="h-4 w-4 text-muted-foreground"
              aria-hidden="true"
            />
            Settings
          </Link>

          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm text-destructive transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
