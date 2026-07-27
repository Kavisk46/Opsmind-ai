"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Info, Sparkles, TrendingUp } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  dashboardInsights,
  type InsightTone,
} from "@/lib/mock-data/mockDashboard";
import { cn } from "@/lib/utils";

import { FadeIn } from "./FadeIn";

const TONE_ICON: Record<InsightTone, typeof TrendingUp> = {
  positive: TrendingUp,
  warning: AlertTriangle,
  info: Info,
};

const TONE_CLASS: Record<InsightTone, string> = {
  positive: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
  info: "bg-info/15 text-info",
};

// A single, premium "AI is watching your knowledge base" panel — deliberately
// one big card rather than a grid of small ones, closer to how ChatGPT
// Enterprise/Copilot surface generated insights as a running feed than a
// dashboard of individual metric tiles.
export function AIInsights() {
  return (
    <FadeIn>
      <Card className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent"
          aria-hidden="true"
        />
        <CardHeader className="relative flex-row items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <Sparkles className="h-4.5 w-4.5" aria-hidden="true" />
          </div>
          <div>
            <CardTitle level="h2">AI Insights</CardTitle>
            <CardDescription>
              Generated from activity across your workspace
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="relative space-y-1">
          {dashboardInsights.map((insight, index) => {
            const Icon = TONE_ICON[insight.tone];
            return (
              <motion.div
                key={insight.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.06 }}
                className="flex items-start gap-3 rounded-md p-2.5 transition-colors hover:bg-accent/50"
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                    TONE_CLASS[insight.tone]
                  )}
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                <p className="text-sm text-foreground">{insight.text}</p>
              </motion.div>
            );
          })}
        </CardContent>
      </Card>
    </FadeIn>
  );
}
