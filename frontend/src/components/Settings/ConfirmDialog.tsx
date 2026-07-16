"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect, useRef } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { trapTabFocus } from "@/hooks/use-focus-trap";
import { useModalStore } from "@/store/modal-store";

export const CONFIRM_DIALOG_MODAL_ID = "confirm-dialog";

interface ConfirmDialogProps {
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
  onConfirm: () => void;
}

// Imperative helper — every admin page calls this from a click handler
// rather than wiring up its own modal-open state, matching how the
// generic useModalStore is meant to be used ("any feature opens a modal
// through this one store instead of getting a dedicated store of its own").
export function openConfirmDialog(props: ConfirmDialogProps) {
  useModalStore
    .getState()
    .openModal(CONFIRM_DIALOG_MODAL_ID, props as unknown as Record<string, unknown>);
}

// Mounted once (see Settings.tsx) — reusable confirmation dialog for any
// destructive-ish action across the settings/admin pages (revoking an API
// key, signing out a session, etc.).
export function ConfirmDialog() {
  const activeModalId = useModalStore((state) => state.activeModalId);
  const modalProps = useModalStore((state) => state.modalProps) as
    | ConfirmDialogProps
    | undefined;
  const closeModal = useModalStore((state) => state.closeModal);
  const isOpen = activeModalId === CONFIRM_DIALOG_MODAL_ID;
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    confirmButtonRef.current?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeModal();
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
  }, [isOpen, closeModal]);

  if (!isOpen || !modalProps) {
    return null;
  }

  const {
    title,
    description,
    confirmLabel = "Confirm",
    cancelLabel = "Cancel",
    variant = "default",
    onConfirm,
  } = modalProps;

  const handleConfirm = () => {
    onConfirm();
    closeModal();
  };

  return (
    <>
      <div
        className="fixed inset-0 z-(--z-modal-backdrop) bg-background/80"
        onClick={closeModal}
        aria-hidden="true"
      />
      <div
        ref={containerRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        className="fixed inset-x-4 top-1/3 z-(--z-modal) mx-auto max-w-sm -translate-y-1/2 rounded-lg border border-border bg-card p-5 shadow-modal animate-scale-in motion-reduce:animate-none sm:inset-x-auto sm:w-full"
      >
        <div className="flex items-start gap-3">
          {variant === "destructive" && (
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <AlertTriangle className="h-4.5 w-4.5" aria-hidden="true" />
            </div>
          )}
          <div className="min-w-0">
            <h2
              id="confirm-dialog-title"
              className="text-sm font-semibold text-foreground"
            >
              {title}
            </h2>
            <p
              id="confirm-dialog-description"
              className="mt-1 text-sm text-muted-foreground"
            >
              {description}
            </p>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={closeModal}>
            {cancelLabel}
          </Button>
          {/* A plain button styled via buttonVariants (not <Button>) so the
              ref used for focus-on-open forwards correctly without adding
              ref support to the shared Button component. */}
          <button
            ref={confirmButtonRef}
            type="button"
            onClick={handleConfirm}
            className={buttonVariants({
              variant: variant === "destructive" ? "destructive" : "primary",
            })}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </>
  );
}
