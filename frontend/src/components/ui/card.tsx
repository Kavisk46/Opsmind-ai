import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card text-card-foreground shadow-card",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-col gap-1 p-4 sm:p-6", className)}
      {...props}
    />
  );
}

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  /** Defaults to h3 — override when a Card's title is the first heading
   * after the page's h1 (no intervening h2 section), so the outline
   * doesn't skip a level. */
  level?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
}

export function CardTitle({ className, level = "h3", ...props }: CardTitleProps) {
  const Heading = level;
  return (
    <Heading
      className={cn("text-sm font-semibold text-foreground", className)}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn("text-sm text-muted-foreground", className)} {...props} />
  );
}

export function CardContent({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-4 pt-0 sm:p-6 sm:pt-0", className)} {...props} />
  );
}
