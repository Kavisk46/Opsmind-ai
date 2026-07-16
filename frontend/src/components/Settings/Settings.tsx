"use client";

import { useState } from "react";

import { ConfirmDialog } from "./ConfirmDialog";
import {
  DEFAULT_SETTINGS_SECTION_ID,
  SETTINGS_SECTIONS,
} from "./settings-sections";
import { SettingsContent } from "./SettingsContent";
import { SettingsNav } from "./SettingsNav";

export function Settings() {
  const [activeSectionId, setActiveSectionId] = useState(
    DEFAULT_SETTINGS_SECTION_ID
  );
  const [isNavOpen, setIsNavOpen] = useState(false);

  const activeSection =
    SETTINGS_SECTIONS.find((section) => section.id === activeSectionId) ??
    SETTINGS_SECTIONS[0];

  const handleSelectSection = (id: string) => {
    setActiveSectionId(id);
    setIsNavOpen(false);
  };

  if (!activeSection) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      <button
        type="button"
        onClick={() => setIsNavOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={isNavOpen}
        className="flex items-center gap-2 rounded-lg border border-border bg-card p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:hidden"
      >
        <activeSection.icon
          className="h-4 w-4 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
        <span className="truncate text-sm font-medium text-foreground">
          {activeSection.label}
        </span>
      </button>

      <div className="hidden lg:block">
        <SettingsNav
          sections={SETTINGS_SECTIONS}
          activeSectionId={activeSectionId}
          onSelectSection={setActiveSectionId}
        />
      </div>

      {isNavOpen && (
        <div
          className="fixed inset-0 z-(--z-modal-backdrop) bg-background/80 lg:hidden"
          onClick={() => setIsNavOpen(false)}
          aria-hidden="true"
        />
      )}
      {isNavOpen && (
        <div className="fixed inset-x-4 top-20 bottom-4 z-(--z-modal) animate-scale-in motion-reduce:animate-none lg:hidden">
          <SettingsNav
            sections={SETTINGS_SECTIONS}
            activeSectionId={activeSectionId}
            onSelectSection={handleSelectSection}
            onClose={() => setIsNavOpen(false)}
          />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <SettingsContent section={activeSection} />
      </div>

      <ConfirmDialog />
    </div>
  );
}
