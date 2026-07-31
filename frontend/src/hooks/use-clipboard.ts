"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { toast } from "@/lib/toast";

interface UseClipboardOptions {
  // How long `copied` stays true — drives the check-mark-then-back-to-
  // copy-icon animation every clipboard button in this app uses.
  resetDelayMs?: number;
}

interface CopyOptions {
  // Overrides the toast text for this one call — e.g. "Copied as
  // Markdown" vs "Copied as plain text" from the same hook instance
  // (see ClipboardMenu, which calls copy() twice with different labels).
  successMessage?: string;
}

interface UseClipboardResult {
  copied: boolean;
  copy: (text: string, options?: CopyOptions) => Promise<void>;
}

// The ONE place this app calls navigator.clipboard.writeText — every
// copy affordance (ClipboardButton, ClipboardMenu, and any one-off use
// like ApiKeysSettings' "copy this new key") goes through this hook
// instead of each re-implementing the try/catch, the toast, and the
// copied-state timer independently. That duplication is exactly what
// existed before this hook: CodeBlock, MessageActions, and
// ApiKeysSettings each had their own small, slightly-different copy
// implementation.
export function useClipboard({
  resetDelayMs = 1500,
}: UseClipboardOptions = {}): UseClipboardResult {
  const [copied, setCopied] = useState(false);
  const resetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (resetTimeoutRef.current) {
        clearTimeout(resetTimeoutRef.current);
      }
    };
  }, []);

  const copy = useCallback(
    async (text: string, options?: CopyOptions) => {
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        // A real, if rare, failure mode: clipboard access can be denied
        // by browser permissions/policy, or navigator.clipboard can be
        // absent entirely on a non-secure (non-HTTPS, non-localhost)
        // origin. Failing silently would leave a user assuming
        // something was copied when nothing was.
        toast("Couldn't copy to clipboard — check your browser permissions.");
        return;
      }

      toast(options?.successMessage ?? "Copied to clipboard");
      setCopied(true);
      if (resetTimeoutRef.current) {
        clearTimeout(resetTimeoutRef.current);
      }
      resetTimeoutRef.current = setTimeout(() => setCopied(false), resetDelayMs);
    },
    [resetDelayMs]
  );

  return { copied, copy };
}
