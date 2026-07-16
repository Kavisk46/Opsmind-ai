"use client";

import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useModalStore } from "@/store/modal-store";

import { UPLOAD_MODAL_ID } from "./UploadModal";

// Split out from KnowledgeBase so the page route can keep PageHeader's
// `actions` slot filled without making the whole page a client component.
export function UploadButton() {
  const openModal = useModalStore((state) => state.openModal);

  return (
    <Button type="button" onClick={() => openModal(UPLOAD_MODAL_ID)} className="gap-2">
      <Upload className="h-4 w-4" aria-hidden="true" />
      Upload
    </Button>
  );
}
