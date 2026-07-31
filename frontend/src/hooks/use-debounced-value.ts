"use client";

import { useEffect, useState } from "react";

// Generic — used to delay firing a search request until the user pauses
// typing, without coupling this to any specific feature's search logic.
export function useDebouncedValue<T>(value: T, delayMs: number = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeoutId = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timeoutId);
  }, [value, delayMs]);

  return debounced;
}
