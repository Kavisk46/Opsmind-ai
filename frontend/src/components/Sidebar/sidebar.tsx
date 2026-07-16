"use client";

import {
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { trapTabFocus } from "@/hooks/use-focus-trap";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";
import { useSidebarStore } from "@/store/sidebar-store";

import {
  footerNavItem,
  isNavItemActive,
  navGroups,
  type NavItem,
} from "./nav-items";

function NavLink({
  item,
  isActive,
  isCollapsed,
  onNavigate,
}: {
  item: NavItem;
  isActive: boolean;
  isCollapsed: boolean;
  onNavigate: () => void;
}) {
  return (
    <Link
      href={item.href}
      title={item.label}
      onClick={onNavigate}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors motion-reduce:transition-none",
        FOCUS_RING_CLASS,
        isActive
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
      )}
    >
      <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span
        className={cn("truncate", isCollapsed ? "hidden" : "hidden md:inline")}
      >
        {item.label}
      </span>
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const isOpen = useSidebarStore((state) => state.isOpen);
  const close = useSidebarStore((state) => state.close);
  const isCollapsed = useSidebarStore((state) => state.isCollapsed);
  const toggleCollapsed = useSidebarStore((state) => state.toggleCollapsed);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set()
  );
  const asideRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    useSidebarStore.persist.rehydrate();
  }, []);

  const toggleGroup = (id: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        close();
        return;
      }
      if (asideRef.current) {
        trapTabFocus(event, asideRef.current);
      }
    }
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, close]);

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-(--z-modal-backdrop) bg-background/80 md:hidden"
          onClick={close}
          aria-hidden="true"
        />
      )}
      <aside
        ref={asideRef}
        id="app-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-(--z-modal) flex w-64 -translate-x-full flex-col border-r border-border bg-card transition-[transform,width] duration-(--duration-base) ease-out motion-reduce:transition-none md:sticky md:top-0 md:h-screen md:translate-x-0",
          isOpen && "translate-x-0",
          isCollapsed ? "md:w-16" : "md:w-64"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-border px-4">
          <Link
            href="/"
            onClick={close}
            className={cn(
              "flex items-center gap-2 rounded-md text-lg font-semibold text-foreground",
              FOCUS_RING_CLASS
            )}
          >
            <Sparkles
              className="h-5 w-5 shrink-0 text-primary"
              aria-hidden="true"
            />
            <span className={cn(isCollapsed ? "hidden" : "hidden md:inline")}>
              OpsMind AI
            </span>
          </Link>

          <button
            ref={closeButtonRef}
            type="button"
            onClick={close}
            aria-label="Close menu"
            className={cn(
              "rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground md:hidden",
              FOCUS_RING_CLASS
            )}
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>

          <button
            type="button"
            onClick={toggleCollapsed}
            aria-expanded={!isCollapsed}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "hidden rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground md:flex",
              FOCUS_RING_CLASS
            )}
          >
            {isCollapsed ? (
              <PanelLeftOpen className="h-5 w-5" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>

        <nav aria-label="Primary" className="flex-1 overflow-y-auto p-3">
          <ul className="space-y-4">
            {navGroups.map((group) => {
              const isExpanded = !collapsedGroups.has(group.id);

              return (
                <li key={group.id}>
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.id)}
                    aria-expanded={isExpanded}
                    aria-controls={`nav-group-${group.id}`}
                    className={cn(
                      "w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground",
                      FOCUS_RING_CLASS,
                      isCollapsed ? "hidden" : "hidden md:flex"
                    )}
                  >
                    <span>{group.label}</span>
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 transition-transform motion-reduce:transition-none",
                        !isExpanded && "-rotate-90"
                      )}
                      aria-hidden="true"
                    />
                  </button>
                  <div
                    id={`nav-group-${group.id}`}
                    className={cn(
                      "grid transition-[grid-template-rows] duration-(--duration-base) ease-out motion-reduce:transition-none",
                      isExpanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                    )}
                  >
                    <ul className="overflow-hidden">
                      {group.items.map((item) => (
                        <li key={item.href}>
                          <NavLink
                            item={item}
                            isActive={isNavItemActive(pathname, item.href)}
                            isCollapsed={isCollapsed}
                            onNavigate={close}
                          />
                        </li>
                      ))}
                    </ul>
                  </div>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-border p-3">
          <NavLink
            item={footerNavItem}
            isActive={isNavItemActive(pathname, footerNavItem.href)}
            isCollapsed={isCollapsed}
            onNavigate={close}
          />
        </div>
      </aside>
    </>
  );
}
