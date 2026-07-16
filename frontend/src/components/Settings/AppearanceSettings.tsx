"use client";

import { Check, Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useState, type FormEvent } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import appearanceData from "@/lib/mock-data/settings-appearance.json";
import { cn } from "@/lib/utils";

import { SettingsFormActions } from "./SettingsFormActions";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";
import { useSettingsSave } from "./use-settings-save";

interface AppearanceData {
  theme: "light" | "dark" | "system";
  density: "comfortable" | "compact";
}

const defaultAppearance = appearanceData as AppearanceData;

const THEME_OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Laptop },
] as const;

const DENSITY_OPTIONS = [
  {
    value: "comfortable",
    label: "Comfortable",
    description: "More whitespace between rows and controls.",
  },
  {
    value: "compact",
    label: "Compact",
    description: "Tighter spacing — fit more on screen.",
  },
] as const;

// Theme is wired to the app's real next-themes instance (the same one the
// navbar's ThemeToggle uses) — it's a genuine preference, not mock. Density
// is preview-only: nothing else in the app currently reads it.
export function AppearanceSettings() {
  const isLoading = useSimulatedLoad();
  const [density, setDensity] = useState<AppearanceData["density"]>(
    defaultAppearance.density
  );
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { status, errorMessage, save } = useSettingsSave();

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await save();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle level="h2">Appearance</CardTitle>
        <CardDescription>
          Theme, density, and other display preferences.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <p className="mb-2 text-sm font-medium text-foreground">Theme</p>
            <div
              role="radiogroup"
              aria-label="Theme"
              className="grid grid-cols-1 gap-3 sm:grid-cols-3"
            >
              {THEME_OPTIONS.map((option) => {
                const isActive = (theme ?? "system") === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="radio"
                    aria-checked={isActive}
                    onClick={() => setTheme(option.value)}
                    className={cn(
                      "flex items-center gap-2.5 rounded-md border px-3 py-2.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      isActive
                        ? "border-primary bg-accent text-accent-foreground"
                        : "border-border hover:bg-accent/50"
                    )}
                  >
                    <option.icon
                      className="h-4 w-4 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <span className="flex-1">{option.label}</span>
                    {isActive && (
                      <Check className="h-4 w-4 shrink-0" aria-hidden="true" />
                    )}
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Currently showing {resolvedTheme === "dark" ? "dark" : "light"}{" "}
              mode.
            </p>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-foreground">
              Density
            </p>
            <div
              role="radiogroup"
              aria-label="Density"
              className="grid grid-cols-1 gap-3 sm:grid-cols-2"
            >
              {DENSITY_OPTIONS.map((option) => {
                const isActive = density === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="radio"
                    aria-checked={isActive}
                    onClick={() => setDensity(option.value)}
                    className={cn(
                      "flex flex-col gap-1 rounded-md border px-3 py-2.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      isActive
                        ? "border-primary bg-accent text-accent-foreground"
                        : "border-border hover:bg-accent/50"
                    )}
                  >
                    <span className="flex items-center justify-between font-medium">
                      {option.label}
                      {isActive && (
                        <Check className="h-4 w-4 shrink-0" aria-hidden="true" />
                      )}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {option.description}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Density is a preview-only preference in this demo — it
              isn&apos;t applied elsewhere yet.
            </p>
          </div>

          <SettingsFormActions status={status} errorMessage={errorMessage} />
        </form>
      </CardContent>
    </Card>
  );
}
