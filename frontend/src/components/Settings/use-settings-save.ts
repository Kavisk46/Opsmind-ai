"use client";

import { useState } from "react";

import { simulateSave } from "./settings-mock-api";

export type SaveStatus = "idle" | "saving" | "success" | "error";

// Shared save-lifecycle state for every settings form — mock only, no real
// request. Each page calls save() from its onSubmit handler.
export function useSettingsSave() {
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const save = async () => {
    setStatus("saving");
    setErrorMessage(null);
    try {
      await simulateSave();
      setStatus("success");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Something went wrong."
      );
      setStatus("error");
    }
  };

  const reset = () => {
    setStatus("idle");
    setErrorMessage(null);
  };

  return { status, errorMessage, save, reset };
}
