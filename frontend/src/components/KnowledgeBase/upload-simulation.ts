const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;
const MAX_FILE_SIZE_LABEL = "20 MB";

const ACCEPTED_EXTENSIONS = [
  ".md",
  ".pdf",
  ".doc",
  ".docx",
  ".xls",
  ".xlsx",
  ".ppt",
  ".pptx",
  ".png",
  ".jpg",
  ".jpeg",
];

export const UPLOAD_ACCEPT_ATTRIBUTE = ACCEPTED_EXTENSIONS.join(",");

function getExtension(filename: string): string {
  const match = /\.[^.]+$/.exec(filename);
  return match ? match[0].toLowerCase() : "";
}

// Deterministic validation (extension + size) rather than a random failure
// chance — reproducible error states are more useful for a demo than flaky
// ones, and this is genuinely realistic client-side validation regardless
// of the mock upload behind it.
export function validateFile(file: File): string | null {
  const extension = getExtension(file.name);

  if (!ACCEPTED_EXTENSIONS.includes(extension)) {
    return `${extension || "This file type"} isn't supported. Accepted types: ${ACCEPTED_EXTENSIONS.join(", ")}.`;
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File is too large — the limit is ${MAX_FILE_SIZE_LABEL}.`;
  }

  return null;
}

const MIN_TICK_MS = 120;
const MAX_TICK_MS = 260;

function randomTickDelay() {
  return MIN_TICK_MS + Math.random() * (MAX_TICK_MS - MIN_TICK_MS);
}

// No network call — just realistic, cancellable progress timing so the
// upload UI has something real to animate.
export function simulateUpload(onProgress: (percent: number) => void) {
  let cancelled = false;
  let timeoutId: ReturnType<typeof setTimeout>;

  const promise = new Promise<void>((resolve) => {
    let percent = 0;

    const tick = () => {
      if (cancelled) {
        return;
      }
      percent = Math.min(100, percent + 8 + Math.random() * 12);
      onProgress(Math.round(percent));

      if (percent >= 100) {
        resolve();
        return;
      }
      timeoutId = setTimeout(tick, randomTickDelay());
    };

    timeoutId = setTimeout(tick, randomTickDelay());
  });

  return {
    promise,
    cancel: () => {
      cancelled = true;
      clearTimeout(timeoutId);
    },
  };
}
