"use client";

import { useEffect, type RefObject } from "react";

import { trapTabFocus } from "./use-focus-trap";

interface UseModalDismissOptions {
  // Optional to match the "mobile drawer" convention (ConversationList,
  // FolderTree, SettingsNav): the desktop instance renders without onClose
  // and this hook is then a no-op; the mobile modal instance provides it.
  onClose?: () => void;
  closeButtonRef: RefObject<HTMLButtonElement | null>;
  // The modal's own outer element — Tab/Shift+Tab stays inside it instead
  // of reaching background content still visible behind the backdrop.
  containerRef: RefObject<HTMLElement | null>;
}

// Shared focus-on-open + Escape-to-close + Tab-trap + body-scroll-lock
// behavior for mobile-drawer-style modals. Consumers with extra cleanup of
// their own (e.g. UploadModal's in-flight upload cancellation) add their own
// separate effect alongside this one rather than folding it in here.
export function useModalDismiss({
  onClose,
  closeButtonRef,
  containerRef,
}: UseModalDismissOptions): void {
  useEffect(() => {
    if (!onClose) {
      return;
    }

    closeButtonRef.current?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose?.();
        return;
      }
      if (containerRef.current) {
        trapTabFocus(event, containerRef.current);
      }
    }
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
    // Mount-only: this instance exists exactly as long as the modal is open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
