import type { Message } from "@/components/Chat/types";

const CANNED_RESPONSES = [
  "Based on your team's knowledge base, here's what I found on that topic.",
  "I've indexed that across your recent documents — would you like a summary?",
  "Good question. Let me pull the most relevant sources for you.",
  "Here's a quick summary based on what's been uploaded recently.",
  "I don't have much context on that yet, but I can search your documents for more detail.",
];

export async function POST(request: Request) {
  let body: { content?: string };
  try {
    body = (await request.json()) as { content?: string };
  } catch {
    return Response.json(
      { error: "Request body must be valid JSON." },
      { status: 400 }
    );
  }

  if (!body.content || body.content.trim().length === 0) {
    return Response.json(
      { error: "Message content is required." },
      { status: 400 }
    );
  }

  // Simulated network/AI latency.
  await new Promise((resolve) => setTimeout(resolve, 900));

  const reply =
    CANNED_RESPONSES[Math.floor(Math.random() * CANNED_RESPONSES.length)] ??
    "I'm here to help — could you rephrase that?";

  const message: Message = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: reply,
    createdAt: new Date().toISOString(),
  };

  return Response.json({ message });
}
