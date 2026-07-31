import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { toast } from "@/lib/toast";

import { useClipboard } from "./use-clipboard";

vi.mock("@/lib/toast", () => ({
  toast: vi.fn(),
}));

const mockedToast = vi.mocked(toast);
const writeTextMock = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
  // Object.defineProperty, not Object.assign — jsdom defines
  // `navigator.clipboard` as a getter-only accessor, so a plain
  // assignment throws "Cannot set property clipboard... which has only
  // a getter" once another test file in the same worker has already
  // touched it. `configurable: true` is what lets THIS override itself
  // be redefined again by the next test file's beforeEach.
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: writeTextMock },
    configurable: true,
    writable: true,
  });
  writeTextMock.mockResolvedValue(undefined);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useClipboard", () => {
  it("writes the given text to the clipboard", async () => {
    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      await result.current.copy("hello world");
    });

    expect(writeTextMock).toHaveBeenCalledWith("hello world");
  });

  it("sets copied to true after a successful copy, then resets after the delay", async () => {
    const { result } = renderHook(() => useClipboard({ resetDelayMs: 1000 }));

    await act(async () => {
      await result.current.copy("hello");
    });
    expect(result.current.copied).toBe(true);

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.copied).toBe(false);
  });

  it("shows a default success toast", async () => {
    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      await result.current.copy("hello");
    });

    expect(mockedToast).toHaveBeenCalledWith("Copied to clipboard");
  });

  it("shows a custom success message when provided", async () => {
    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      await result.current.copy("hello", { successMessage: "Copied as Markdown" });
    });

    expect(mockedToast).toHaveBeenCalledWith("Copied as Markdown");
  });

  it("shows a failure toast and does not set copied when the clipboard write rejects", async () => {
    writeTextMock.mockRejectedValueOnce(new Error("denied"));
    const { result } = renderHook(() => useClipboard());

    await act(async () => {
      await result.current.copy("hello");
    });

    expect(result.current.copied).toBe(false);
    expect(mockedToast).toHaveBeenCalledWith(
      "Couldn't copy to clipboard — check your browser permissions."
    );
  });

  it("restarts the reset timer on a second copy before the first resets", async () => {
    const { result } = renderHook(() => useClipboard({ resetDelayMs: 1000 }));

    await act(async () => {
      await result.current.copy("first");
    });
    act(() => {
      vi.advanceTimersByTime(700);
    });
    await act(async () => {
      await result.current.copy("second");
    });
    act(() => {
      vi.advanceTimersByTime(700);
    });
    // 1400ms total have passed, but the second copy reset the 1000ms
    // timer at the 700ms mark — it shouldn't fire until 1700ms.
    expect(result.current.copied).toBe(true);

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current.copied).toBe(false);
  });
});
