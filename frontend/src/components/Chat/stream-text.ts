const MIN_CHUNK_DELAY_MS = 25;
const MAX_CHUNK_DELAY_MS = 70;

function randomDelay() {
  return (
    MIN_CHUNK_DELAY_MS + Math.random() * (MAX_CHUNK_DELAY_MS - MIN_CHUNK_DELAY_MS)
  );
}

// Splits on whitespace but keeps the whitespace as its own segment, so
// re-joining the revealed slices reproduces the original text exactly.
function splitIntoChunks(text: string) {
  return text.split(/(\s+)/).filter((chunk) => chunk.length > 0);
}

// Fakes token-by-token streaming for a full response string that already
// arrived from the mock API — reveals it word by word on randomized short
// delays and reports the growing partial string on each tick.
export function streamText(
  text: string,
  onChunk: (partial: string) => void,
  onDone: () => void
): () => void {
  const chunks = splitIntoChunks(text);
  let index = 0;
  let timeoutId: ReturnType<typeof setTimeout>;

  const tick = () => {
    index += 1;
    onChunk(chunks.slice(0, index).join(""));

    if (index >= chunks.length) {
      onDone();
      return;
    }

    timeoutId = setTimeout(tick, randomDelay());
  };

  timeoutId = setTimeout(tick, randomDelay());

  return () => clearTimeout(timeoutId);
}
