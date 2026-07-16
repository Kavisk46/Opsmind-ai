import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}

// Shared card shell for every auth page: title/subtitle header, form body,
// and an optional footer slot (e.g. "Don't have an account? Sign up").
export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle level="h1" className="text-xl">
          {title}
        </CardTitle>
        {subtitle && <CardDescription>{subtitle}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-5">{children}</CardContent>
      {footer && (
        <div className="border-t border-border p-4 text-center text-sm text-muted-foreground sm:p-6 sm:pt-4">
          {footer}
        </div>
      )}
    </Card>
  );
}
