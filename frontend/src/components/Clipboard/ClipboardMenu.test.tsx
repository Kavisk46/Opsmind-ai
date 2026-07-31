import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ClipboardMenu } from "./ClipboardMenu";

vi.mock("@/lib/toast", () => ({
  toast: vi.fn(),
}));

const writeTextMock = vi.fn();
const markdown = "# Title\n\nThis is **bold** text.";

// userEvent.setup() installs its OWN navigator.clipboard stub internally
// (verified directly) — so the mock has to be (re)installed AFTER
// setup(), not in a plain beforeEach that runs before it, or every
// write goes to userEvent's stub instead of ours.
function setupClipboard() {
  const user = userEvent.setup();
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: writeTextMock },
    configurable: true,
    writable: true,
  });
  return user;
}

beforeEach(() => {
  vi.clearAllMocks();
  writeTextMock.mockResolvedValue(undefined);
});

describe("ClipboardMenu", () => {
  it("is closed by default", () => {
    render(<ClipboardMenu markdown={markdown} ariaLabel="Copy message" />);

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("opens the menu when the trigger is clicked", async () => {
    const user = setupClipboard();
    render(<ClipboardMenu markdown={markdown} ariaLabel="Copy message" />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));

    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Copy as Markdown" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Copy as Plain Text" })).toBeInTheDocument();
  });

  it("copies the raw markdown source when 'Copy as Markdown' is chosen", async () => {
    const user = setupClipboard();
    render(<ClipboardMenu markdown={markdown} ariaLabel="Copy message" />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));
    await user.click(screen.getByRole("menuitem", { name: "Copy as Markdown" }));

    // The menu item's click handler fires copy() without awaiting it —
    // waitFor gives the internal navigator.clipboard.writeText()
    // promise a chance to resolve before asserting.
    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalledWith(markdown);
    });
  });

  it("copies stripped plain text when 'Copy as Plain Text' is chosen", async () => {
    const user = setupClipboard();
    render(<ClipboardMenu markdown={markdown} ariaLabel="Copy message" />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));
    await user.click(screen.getByRole("menuitem", { name: "Copy as Plain Text" }));

    await waitFor(() => expect(writeTextMock).toHaveBeenCalled());
    const copiedText = writeTextMock.mock.calls[0]?.[0] as string;
    expect(copiedText).not.toContain("#");
    expect(copiedText).not.toContain("**");
    expect(copiedText).toContain("Title");
    expect(copiedText).toContain("bold");
  });

  it("closes the menu after a selection is made", async () => {
    const user = setupClipboard();
    render(<ClipboardMenu markdown={markdown} ariaLabel="Copy message" />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));
    await user.click(screen.getByRole("menuitem", { name: "Copy as Markdown" }));

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes the menu on Escape", async () => {
    const user = setupClipboard();
    render(<ClipboardMenu markdown={markdown} ariaLabel="Copy message" />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));
    expect(screen.getByRole("menu")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("does not open when disabled", async () => {
    const user = setupClipboard();
    render(<ClipboardMenu markdown={markdown} ariaLabel="Copy message" disabled />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
