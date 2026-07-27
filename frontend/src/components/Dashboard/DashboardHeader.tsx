"use client";

import { Sparkles } from "lucide-react";

import { useAuth } from "@/components/Providers/AuthProvider";
import { Card, CardContent } from "@/components/ui/card";
import { workspace } from "@/lib/mock-data/mockDashboard";

import { FadeIn } from "./FadeIn";
import { QuickActions } from "./QuickActions";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function DashboardHeader() {
  const { user, isGuest } = useAuth();
  const firstName = isGuest || !user ? "there" : user.name.split(" ")[0];

  return (
    <FadeIn>
      <Card className="overflow-hidden border-transparent bg-primary text-primary-foreground">
        <CardContent className="flex flex-col gap-6 p-6 sm:p-8">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-1 h-6 w-6 shrink-0" aria-hidden="true" />
            <div className="min-w-0">
              <p className="text-sm text-primary-foreground/70">
                {getGreeting()}, {firstName}
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
                {workspace.name}
              </h1>
              <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-primary-foreground/80">
                <span>{workspace.team}</span>
                <span aria-hidden="true">·</span>
                <span>{workspace.plan} plan</span>
              </p>
            </div>
          </div>

          <QuickActions className="[&>a]:bg-primary-foreground/10 [&>a]:text-primary-foreground [&>a:hover]:bg-primary-foreground/20" />
        </CardContent>
      </Card>
    </FadeIn>
  );
}
