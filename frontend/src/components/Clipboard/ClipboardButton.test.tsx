import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ClipboardButton } from "./ClipboardButton";

const writeTextMock = vi.fn();

// userEvent.setup() installs its OWN navigator.clipboard stub internally
// (verified directly — logging navigator.clipboard.writeText right after
// setup() showed it was no longer our mock) — so the mock has to be
// (re)installed AFTER setup(), not in a plain beforeEach that runs
// before it, or every write goes to userEvent's stub instead of ours.
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

describe("ClipboardButton", () => {
  it("copies the given text when clicked", async () => {
    const user = setupClipboard();
    render(<ClipboardButton text="hello world" ariaLabel="Copy message" />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));

    // The click handler fires copy() without awaiting it (a real
    // fire-and-forget UI action, not something the click event itself
    // should block on) — waitFor gives its internal
    // navigator.clipboard.writeText() promise a chance to resolve
    // before asserting, rather than checking synchronously the instant
    // the click event finishes dispatching.
    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalledWith("hello world");
    });
  });

  it("copies the given text via the 'c' keyboard shortcut while focused", async () => {
    const user = setupClipboard();
    render(<ClipboardButton text="hello world" ariaLabel="Copy message" />);

    const button = screen.getByRole("button", { name: "Copy message" });
    button.focus();
    await user.keyboard("c");

    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalledWith("hello world");
    });
  });

  it("renders a visible label when provided", () => {
    render(
      <ClipboardButton
        text="const x = 1;"
        ariaLabel="Copy code"
        label="Copy"
        variant="inline"
      />
    );

    expect(screen.getByText("Copy")).toBeInTheDocument();
  });

  it("does not copy when disabled", async () => {
    const user = setupClipboard();
    render(<ClipboardButton text="hello" ariaLabel="Copy message" disabled />);

    await user.click(screen.getByRole("button", { name: "Copy message" }));

    expect(writeTextMock).not.toHaveBeenCalled();
  });
});
