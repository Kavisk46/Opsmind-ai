import { BarChart3, Sparkles } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export function HeroSection() {
  const today = formatDate(new Date(), {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <Card className="border-transparent bg-primary text-primary-foreground">
      <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <Sparkles className="mt-0.5 h-6 w-6 shrink-0" aria-hidden="true" />
          <div>
            <p className="text-xs text-primary-foreground/70">{today}</p>
            <p className="mt-0.5 text-lg font-semibold">Welcome back</p>
            <p className="mt-1 text-sm text-primary-foreground/80">
              Your AI assistant has answered 1,204 questions today. Ask it
              something new, or catch up on what your team shipped.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Link
            href="/assistant"
            className={cn(buttonVariants({ variant: "secondary" }))}
          >
            Ask AI Assistant
          </Link>
          <Link
            href="/analytics"
            className={cn(
              buttonVariants({ variant: "ghost" }),
              "text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
            )}
          >
            <BarChart3 className="h-4 w-4" aria-hidden="true" />
            View Analytics
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
