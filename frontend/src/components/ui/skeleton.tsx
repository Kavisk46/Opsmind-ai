import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

// Purely decorative — the labeled, standalone unit is whatever composes
// these (see SkeletonCard below), not each individual block.
export function Skeleton({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-pulse motion-reduce:animate-none rounded-md bg-muted",
        className
      )}
      {...props}
    />
  );
}

interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

export function SkeletonText({ lines = 3, className }: SkeletonTextProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          className={cn("h-4", index === lines - 1 ? "w-2/3" : "w-full")}
        />
      ))}
    </div>
  );
}

interface SkeletonAvatarProps {
  size?: number;
  className?: string;
}

export function SkeletonAvatar({ size = 40, className }: SkeletonAvatarProps) {
  return (
    <Skeleton
      className={cn("shrink-0 rounded-full", className)}
      style={{ width: size, height: size }}
    />
  );
}

interface SkeletonCardProps {
  className?: string;
  label?: string;
}

// The composed unit meant to be used standalone — carries the one
// accessible "loading" announcement for the whole card shape.
export function SkeletonCard({
  className,
  label = "Loading",
}: SkeletonCardProps) {
  return (
    <div
      role="status"
      aria-label={label}
      className={cn(
        "flex items-start gap-4 rounded-lg border border-border bg-card p-4 shadow-card",
        className
      )}
    >
      <SkeletonAvatar />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <SkeletonText lines={2} />
      </div>
    </div>
  );
}
