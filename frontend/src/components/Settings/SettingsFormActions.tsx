import { AlertCircle, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

import type { SaveStatus } from "./use-settings-save";

interface SettingsFormActionsProps {
  status: SaveStatus;
  errorMessage?: string | null;
  disabled?: boolean;
}

// Reused at the bottom of every settings form: a Save button plus the
// success/error placeholder for the mock save outcome.
export function SettingsFormActions({
  status,
  errorMessage,
  disabled,
}: SettingsFormActionsProps) {
  const isSaving = status === "saving";

  return (
    <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
      <div aria-live="polite" className="text-sm">
        {status === "success" && (
          <span className="inline-flex items-center gap-1.5 text-success">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            Changes saved.
          </span>
        )}
        {status === "error" && (
          <span className="inline-flex items-center gap-1.5 text-destructive">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            {errorMessage ?? "Something went wrong. Please try again."}
          </span>
        )}
      </div>
      <Button
        type="submit"
        disabled={disabled || isSaving}
        className="gap-2 sm:self-end"
      >
        {isSaving && <Spinner size="sm" />}
        {isSaving ? "Saving…" : "Save changes"}
      </Button>
    </div>
  );
}
