"use client";

import { Lightbulb } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { toast } from "@/lib/toast";
import { cn } from "@/lib/utils";

export interface InsightCardProps {
  title: string;
  description: string;
  category: string;
  categoryVariant: BadgeProps["variant"];
  confidence: number;
  actions: string[];
}

export function InsightCard({
  title,
  description,
  category,
  categoryVariant,
  confidence,
  actions,
}: InsightCardProps) {
  return (
    <Card>
      <CardContent className="p-4 pt-4 sm:p-4 sm:pt-4">
        <div className="flex items-start justify-between gap-2">
          <Lightbulb
            className="h-4 w-4 shrink-0 text-primary"
            aria-hidden="true"
          />
          <Badge variant={categoryVariant}>{category}</Badge>
        </div>
        <p className="mt-2 text-sm font-medium text-foreground">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>

        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Confidence</span>
            <span className="text-muted-foreground">{confidence}%</span>
          </div>
          <Progress value={confidence} label={`Confidence ${confidence}%`} />
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {actions.map((action, index) => (
            <button
              key={action}
              type="button"
              onClick={() => toast(`${action} — coming soon.`)}
              className={cn(
                buttonVariants({
                  variant: index === 0 ? "secondary" : "ghost",
                  size: "sm",
                })
              )}
            >
              {action}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
