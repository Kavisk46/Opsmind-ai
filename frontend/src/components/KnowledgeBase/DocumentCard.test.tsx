import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DocumentCard } from "./DocumentCard";
import { downloadDocument } from "./documents-api";
import type { Document } from "./types";

vi.mock("./documents-api", () => ({
  downloadDocument: vi.fn(),
}));

const mockedDownloadDocument = vi.mocked(downloadDocument);

const document: Document = {
  id: "doc-1",
  title: "Quarterly Report",
  folderId: "",
  categoryId: "",
  tagIds: [],
  fileType: "pdf",
  author: "Ava Thompson",
  updatedAt: "2026-07-28T00:00:00.000Z",
  sizeLabel: "1.2 MB",
  excerpt: "Ready — fully indexed and searchable.",
};

function renderCard(overrides: Partial<Parameters<typeof DocumentCard>[0]> = {}) {
  const onOpen = vi.fn();
  const onToggleFavorite = vi.fn();
  const onDelete = vi.fn();
  render(
    <DocumentCard
      document={document}
      categoryName={undefined}
      tagNames={[]}
      isFavorite={false}
      onOpen={onOpen}
      onToggleFavorite={onToggleFavorite}
      onDelete={onDelete}
      {...overrides}
    />
  );
  return { onOpen, onToggleFavorite, onDelete };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DocumentCard", () => {
  it("renders the document title and excerpt", () => {
    renderCard();
    expect(screen.getByText("Quarterly Report")).toBeInTheDocument();
    expect(
      screen.getByText("Ready — fully indexed and searchable.")
    ).toBeInTheDocument();
  });

  it("calls onOpen when the main card body is clicked", async () => {
    const user = userEvent.setup();
    const { onOpen } = renderCard();

    await user.click(screen.getByText("Quarterly Report"));

    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("triggers a real download without opening the document when the download button is clicked", async () => {
    const user = userEvent.setup();
    const { onOpen } = renderCard();

    await user.click(screen.getByRole("button", { name: "Download Quarterly Report" }));

    expect(mockedDownloadDocument).toHaveBeenCalledWith("doc-1");
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("calls onDelete without opening the document when the delete button is clicked", async () => {
    const user = userEvent.setup();
    const { onOpen, onDelete } = renderCard();

    await user.click(screen.getByRole("button", { name: "Delete Quarterly Report" }));

    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("toggles the favorite state without opening the document", async () => {
    const user = userEvent.setup();
    const { onOpen, onToggleFavorite } = renderCard();

    await user.click(screen.getByRole("button", { name: "Add to favorites" }));

    expect(onToggleFavorite).toHaveBeenCalledTimes(1);
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("reflects an already-favorited document via aria-pressed and label", () => {
    renderCard({ isFavorite: true });
    const favoriteButton = screen.getByRole("button", {
      name: "Remove from favorites",
    });
    expect(favoriteButton).toHaveAttribute("aria-pressed", "true");
  });
});
