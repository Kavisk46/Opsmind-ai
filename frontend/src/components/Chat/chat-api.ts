import { apiClient } from "@/lib/api";

import type { Citation } from "./types";

// Wire shapes verified directly against backend/schemas/chat.py and
// backend/schemas/conversation.py — never guessed. snake_case here
// matches the backend's Pydantic field names exactly; everything else in
// this app works with the camelCase `Citation` type from ./types.
interface CitationWire {
  document_id: string;
  document_name: string;
  chunk_index: number;
  page_number: number | null;
}

interface ChatResponseWire {
  conversation_id: string;
  answer: string;
  citations: CitationWire[];
  tool_used: string;
}

interface ConversationResponseWire {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

function toCitation(citation: CitationWire): Citation {
  return {
    documentId: citation.document_id,
    documentName: citation.document_name,
    chunkIndex: citation.chunk_index,
    pageNumber: citation.page_number,
  };
}

// A dedicated "create an empty conversation" call (POST /conversations) —
// used by ChatWindow to obtain a real conversation_id BEFORE the first
// /chat/stream call of a session. This sidesteps a real cross-origin gap:
// the streaming endpoint's conversation id normally arrives via the
// X-Conversation-ID response header (see api/routes/chat.py), but the
// backend's CORSMiddleware config (main.py) doesn't list that header in
// allow_headers/expose_headers, so a browser reading a cross-origin
// response cannot see it (verified — response.headers.get(...) would
// silently return null in production, where frontend and backend are on
// different origins). POST /conversations returns the id as an ordinary
// JSON body field instead, which has no such restriction, and it exists
// in the backend specifically for "a client that wants a conversation to
// exist ... before the user has typed a first question yet" (see
// api/routes/conversations.py's docstring) — exactly this use case.
export async function createConversation(options?: {
  signal?: AbortSignal;
}): Promise<{ id: string }> {
  const conversation = await apiClient.post<ConversationResponseWire>(
    "/conversations",
    {},
    { signal: options?.signal }
  );
  return { id: conversation.id };
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

function toConversation(conversation: ConversationResponseWire): Conversation {
  return {
    id: conversation.id,
    title: conversation.title,
    createdAt: conversation.created_at,
    updatedAt: conversation.updated_at,
  };
}

// GET /conversations — every conversation the current user owns. Used by
// activity-api.ts to build a real activity feed entry per conversation
// (there's no per-message activity log; a conversation's updated_at is
// the closest real "last activity happened here" signal the backend has
// — see ConversationService.append_message, which is what bumps it).
export async function listConversations(options?: {
  signal?: AbortSignal;
}): Promise<Conversation[]> {
  const conversations = await apiClient.get<ConversationResponseWire[]>(
    "/conversations",
    { signal: options?.signal }
  );
  return conversations.map(toConversation);
}

export interface SendChatMessageResult {
  conversationId: string;
  answer: string;
  citations: Citation[];
  toolUsed: string;
}

// Non-streaming path — POST /chat. Kept alongside streamChatMessage()
// below (not deleted) as a plain fallback any future caller can use
// without needing to handle SSE parsing.
export async function sendChatMessage(
  question: string,
  conversationId: string | undefined,
  options?: { signal?: AbortSignal }
): Promise<SendChatMessageResult> {
  const response = await apiClient.post<ChatResponseWire>(
    "/chat",
    { question, conversation_id: conversationId ?? null },
    { signal: options?.signal }
  );

  return {
    conversationId: response.conversation_id,
    answer: response.answer,
    citations: response.citations.map(toCitation),
    toolUsed: response.tool_used,
  };
}

export interface ChatStreamHandlers {
  onDelta: (delta: string) => void;
  onDone: (result: { citations: Citation[]; toolUsed: string }) => void;
}

// Frame shapes for POST /chat/stream's Server-Sent Events — verified
// directly against api/routes/chat.py's `_sse_event`/`_stream_chat_response`
// and tests/test_chat_streaming.py, never guessed. Each SSE frame is
// `data: <json>\n\n`; the JSON is one of exactly three shapes.
type ChatStreamFrame =
  | { delta: string }
  | { error: string }
  | { done: true; tool_used: string; citations: CitationWire[] };

// Streaming path — POST /chat/stream. Reuses apiClient (via
// apiClient.postStream(), see lib/api/client.ts) for the base URL,
// Authorization header attachment, and connection-level retry/401
// handling; reads the SSE body itself since apiClient's normal
// request()/parseResponse() only knows how to parse one complete JSON (or
// text) body, not an incremental event stream.
//
// `signal` is the caller's own AbortController.signal (see
// ChatWindow.tsx) — this is what cancellation is built on: aborting it
// stops the underlying fetch, which ends the reader loop below via a
// thrown AbortError, same as any other cancelled request in this app.
export async function streamChatMessage(
  input: { question: string; conversationId: string },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const response = await apiClient.postStream(
    "/chat/stream",
    { question: input.question, conversation_id: input.conversationId },
    { signal }
  );

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error(
      "Streaming isn't supported in this browser — please try a different one."
    );
  }

  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");

      if (!rawEvent.startsWith("data: ")) {
        continue;
      }
      const frame = JSON.parse(rawEvent.slice("data: ".length)) as ChatStreamFrame;

      if ("delta" in frame) {
        handlers.onDelta(frame.delta);
      } else if ("done" in frame) {
        handlers.onDone({
          toolUsed: frame.tool_used,
          citations: frame.citations.map(toCitation),
        });
      } else {
        // The backend only sends this after streaming has already started
        // (see _stream_chat_response's `except` branch) — by then the
        // response is already a 200 text/event-stream, so this is the
        // ONLY way a mid-stream failure can reach the caller; there's no
        // separate HTTP error status left to throw from.
        throw new Error(frame.error);
      }
    }
  }
}
