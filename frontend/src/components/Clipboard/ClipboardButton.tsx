"use client";

import { Check, Copy, type LucideIcon } from "lucide-react";
import type { KeyboardEvent } from "react";

import { useClipboard } from "@/hooks/use-clipboard";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

interface ClipboardButtonProps {
  // The exact text this button copies — callers pass whatever's already
  // in hand (message content, a code block's source, an API key), so
  // this component never needs to know where the text came from.
  text: string;
  // Required, not derived from `label` — a button showing only an icon
  // (the common case: MessageActions' copy button, CodeBlock's copy
  // button) has no visible text a screen reader could fall back to, so
  // this can't be optional the way it could be if a visible label
  // always existed.
  ariaLabel: string;
  // Visible text next to the icon — omit for an icon-only button.
  label?: string;
  successMessage?: string;
  icon?: LucideIcon;
  variant?: "icon" | "inline";
  disabled?: boolean;
  className?: string;
}

// The single reusable "copy this exact text" affordance — every simple,
// one-action copy button in this app (a code block, a citation excerpt,
// an API key, a user's own chat message) renders through this component
// rather than each hand-rolling its own icon-swap-on-click button. For
// content where "copy AS Markdown" vs "copy AS Plain Text" is a
// meaningful choice (an assistant's markdown-formatted reply), use
// ClipboardMenu instead — this component always copies `text` verbatim.
export function ClipboardButton({
  text,
  ariaLabel,
  label,
  successMessage,
  icon: Icon = Copy,
  variant = "icon",
  disabled = false,
  className,
}: ClipboardButtonProps) {
  const { copied, copy } = useClipboard();

  const handleCopy = () => {
    void copy(text, { successMessage });
  };

  // Enter/Space already activate a <button> natively — this adds "c" as
  // an extra, discoverable shortcut while the button is focused, the
  // same "focused-element shortcut" pattern sites like YouTube use for
  // their own player controls. Not a global hotkey (which would risk
  // colliding with the browser's or OS's own bindings), and never fires
  // while the user is typing in a text field, since a clipboard button
  // being focused already means focus isn't there.
  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if ((event.key === "c" || event.key === "C") && !event.metaKey && !event.ctrlKey) {
      event.preventDefault();
      handleCopy();
    }
  };

  const ShownIcon = copied ? Check : Icon;

  if (variant === "inline") {
    return (
      <button
        type="button"
        onClick={handleCopy}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-label={ariaLabel}
        className={cn(
          "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50",
          FOCUS_RING_CLASS,
          className
        )}
      >
        <ShownIcon className="h-3.5 w-3.5" aria-hidden="true" />
        {label && <span>{copied ? "Copied" : label}</span>}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      onKeyDown={handleKeyDown}
      disabled={disabled}
      aria-label={ariaLabel}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50",
        FOCUS_RING_CLASS,
        className
      )}
    >
      <ShownIcon className="h-3.5 w-3.5" aria-hidden="true" />
    </button>
  );
}
