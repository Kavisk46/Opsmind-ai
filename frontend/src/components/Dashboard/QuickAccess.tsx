import Link from "next/link";

import { quickAccessTiles } from "@/lib/mock-data/mockDashboard";

import { FadeIn } from "./FadeIn";

export function QuickAccess() {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-foreground">
        Quick Access
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {quickAccessTiles.map((tile, index) => (
          <FadeIn key={tile.id} delay={index * 0.03}>
            <Link
              href={tile.href}
              className="group flex h-full flex-col gap-2 rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-accent-foreground transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <tile.icon className="h-4.5 w-4.5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">
                  {tile.label}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {tile.description}
                </p>
              </div>
            </Link>
          </FadeIn>
        ))}
      </div>
    </div>
  );
}
