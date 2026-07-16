"use client";

import { useEffect, useState } from "react";

export const DEFAULT_LOAD_DELAY_MS = 500;

// Every page/section that renders from mock data shows a brief skeleton
// first, so the loading state is actually observable — one shared
// implementation instead of each feature re-implementing the same
// setTimeout-based delay.
export function useSimulatedLoad(delayMs: number = DEFAULT_LOAD_DELAY_MS): boolean {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const timeoutId = setTimeout(() => {
      if (!cancelled) {
        setIsLoading(false);
      }
    }, delayMs);
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [delayMs]);

  return isLoading;
}
