const LOAD_DELAY_MS = 500;
const SAVE_DELAY_MS = 700;
// A small, deliberate chance of failure — real enough that the error
// placeholder is a genuinely reachable path, not dead code, without making
// every save annoyingly unreliable.
const SAVE_FAILURE_RATE = 0.12;

export function simulateLoadDelay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, LOAD_DELAY_MS));
}

export function simulateSave(): Promise<void> {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (Math.random() < SAVE_FAILURE_RATE) {
        reject(
          new Error("Something went wrong while saving. Please try again.")
        );
      } else {
        resolve();
      }
    }, SAVE_DELAY_MS);
  });
}
