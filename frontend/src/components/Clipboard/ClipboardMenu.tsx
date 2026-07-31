"use client";

import { Check, ChevronDown, Copy } from "lucide-react";
import { useId, useRef, type KeyboardEvent } from "react";

import { useClipboard } from "@/hooks/use-clipboard";
import { useDisclosure } from "@/hooks/use-disclosure";
import { markdownToPlainText } from "@/lib/markdown-to-plain-text";
import { FOCUS_RING_CLASS, POPOVER_ITEM_CLASS, POPOVER_PANEL_CLASS, cn } from "@/lib/utils";

interface ClipboardMenuProps {
  // The raw markdown source — e.g. an assistant chat message's content,
  // exactly as MarkdownRenderer renders it. "Copy as Markdown" copies
  // this verbatim; "Copy as Plain Text" derives a stripped version from
  // it (see lib/markdown-to-plain-text.ts) rather than needing a second
  // plain-text copy of the same content passed in separately.
  markdown: string;
  // Labels BOTH the trigger button (for a screen reader landing on it
  // before the menu is open) and the menu panel once opened.
  ariaLabel: string;
  disabled?: boolean;
  className?: string;
}

// The reusable "this content is markdown, and copying it as markdown vs
// as plain text are both genuinely useful" affordance — used wherever
// this app copies AI-GENERATED markdown content (an assistant's chat
// reply today; document summaries/search answers once those surfaces
// exist). For content with no markdown/plain-text distinction (a code
// block, a user's own plain-text message, an API key), ClipboardButton
// is the right component instead — this one always offers exactly two
// choices, never a single bare "Copy".
//
// Built on useDisclosure() (hooks/use-disclosure.ts) and
// POPOVER_PANEL_CLASS/POPOVER_ITEM_CLASS (lib/utils.ts) — the same
// outside-click/Escape/focus-return behavior and panel styling every
// other dropdown in this app (UserProfileDropdown, NotificationButton,
// the Knowledge Base filter menus) already uses, not a second,
// independently-behaving popover implementation.
export function ClipboardMenu({
  markdown,
  ariaLabel,
  disabled = false,
  className,
}: ClipboardMenuProps) {
  const { copied, copy } = useClipboard();
  const { isOpen, toggle, close, containerRef, triggerRef } = useDisclosure();
  const panelId = useId();
  const firstItemRef = useRef<HTMLButtonElement>(null);
  const secondItemRef = useRef<HTMLButtonElement>(null);

  const handleCopyMarkdown = () => {
    void copy(markdown, { successMessage: "Copied as Markdown" });
    close();
    triggerRef.current?.focus();
  };

  const handleCopyPlainText = () => {
    void copy(markdownToPlainText(markdown), { successMessage: "Copied as plain text" });
    close();
    triggerRef.current?.focus();
  };

  // Arrow keys move focus between the two menu items — the two buttons
  // are the only focusable content, so wrapping between them (rather
  // than stopping at the ends) is standard menu behavior with minimal
  // extra code for a 2-item menu.
  const handleItemKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    otherItem: HTMLButtonElement | null
  ) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      otherItem?.focus();
    }
  };

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => {
          toggle();
          // useDisclosure() only moves focus back to the trigger on
          // close (Escape/outside-click) — opening still needs the
          // first item focused explicitly so keyboard users land inside
          // the menu, not stuck on the trigger.
          requestAnimationFrame(() => firstItemRef.current?.focus());
        }}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={panelId}
        className={cn(
          "inline-flex h-8 items-center gap-0.5 rounded px-1.5 transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50",
          FOCUS_RING_CLASS,
          className
        )}
      >
        {copied ? (
          <Check className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <Copy className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        <ChevronDown className="h-3 w-3" aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          id={panelId}
          role="menu"
          aria-label={ariaLabel}
          className={cn(POPOVER_PANEL_CLASS, "absolute top-full right-0 mt-1 w-44 p-1")}
        >
          <button
            ref={firstItemRef}
            type="button"
            role="menuitem"
            onClick={handleCopyMarkdown}
            onKeyDown={(event) => handleItemKeyDown(event, secondItemRef.current)}
            className={cn(POPOVER_ITEM_CLASS, "justify-start", FOCUS_RING_CLASS)}
          >
            Copy as Markdown
          </button>
          <button
            ref={secondItemRef}
            type="button"
            role="menuitem"
            onClick={handleCopyPlainText}
            onKeyDown={(event) => handleItemKeyDown(event, firstItemRef.current)}
            className={cn(POPOVER_ITEM_CLASS, "justify-start", FOCUS_RING_CLASS)}
          >
            Copy as Plain Text
          </button>
        </div>
      )}
    </div>
  );
}
