import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api";

import type { Citation, Message, MessageRole } from "./types";

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
//
// `title` should be the first question, truncated — matches exactly what
// ConversationService.get_or_create_conversation does server-side when
// IT creates a conversation on the fly (title_hint[:80]); that path never
// runs for a conversation created here, since this app always pre-creates
// one and passes a real conversation_id to every /chat(/stream) call, so
// the backend's own auto-titling never gets a chance to fire. Omitting
// this would leave every conversation titled the backend's generic
// "New conversation" default forever.
export async function createConversation(options?: {
  title?: string;
  signal?: AbortSignal;
}): Promise<{ id: string; title: string }> {
  const conversation = await apiClient.post<ConversationResponseWire>(
    "/conversations",
    { title: options?.title?.slice(0, 80) },
    { signal: options?.signal }
  );
  return { id: conversation.id, title: conversation.title };
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
// — see ConversationService.append_message, which is what bumps it) and
// by AssistantConsole.tsx for the real conversation sidebar.
export async function listConversations(options?: {
  signal?: AbortSignal;
}): Promise<Conversation[]> {
  const conversations = await apiClient.get<ConversationResponseWire[]>(
    "/conversations",
    { signal: options?.signal }
  );
  return conversations.map(toConversation);
}

// AssistantConsole.tsx uses this key as its cache's source of truth for
// the sidebar (via queryClient.setQueryData/invalidateQueries after a
// create/delete) rather than keeping a second, parallel local copy of
// the same list that could drift out of sync with it.
export const CONVERSATIONS_QUERY_KEY = ["conversations"] as const;

export function useConversations() {
  return useQuery({
    queryKey: CONVERSATIONS_QUERY_KEY,
    queryFn: ({ signal }) => listConversations({ signal }),
  });
}

interface MessageResponseWire {
  role: string;
  content: string;
  created_at: string;
}

interface ConversationDetailWire extends ConversationResponseWire {
  messages: MessageResponseWire[];
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

// GET /conversations/{id} — full message history for one conversation.
// backend/schemas/conversation.py's MessageResponse has no `id` and no
// citations field at all (citations are only ever returned alongside the
// LIVE answer that produced them, in ChatResponse/the stream's `done`
// event — never persisted per-message), so a historical message loaded
// here can never show its citations, only ones asked in the current
// session can. `id` is synthesized client-side (stable per index, never
// sent anywhere) purely so React has a key and MessageBubble's existing
// Pick<Message, ...> shape is satisfied.
export async function getConversation(
  conversationId: string,
  options?: { signal?: AbortSignal }
): Promise<ConversationDetail> {
  const conversation = await apiClient.get<ConversationDetailWire>(
    `/conversations/${conversationId}`,
    { signal: options?.signal }
  );

  return {
    ...toConversation(conversation),
    messages: conversation.messages.map((message, index) => ({
      id: `${conversation.id}-${index}`,
      role: message.role as MessageRole,
      content: message.content,
      createdAt: message.created_at,
    })),
  };
}

// Used by ChatWindow.tsx to load a selected conversation's real history.
// `enabled: id !== null` is what lets ChatWindow call this unconditionally
// (a brand-new, not-yet-created chat has conversationId=null) without an
// extra guard at the call site; react-query simply never fires the
// request in that case. Caching this means re-selecting a conversation
// already opened earlier in the session shows its history instantly
// instead of re-fetching and flashing "Loading conversation…" again.
export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: ({ signal }) => getConversation(conversationId as string, { signal }),
    enabled: conversationId !== null,
  });
}

// PATCH /conversations/{id} — renames a conversation. Backend rejects an
// empty/whitespace title with 400 (schemas/conversation.py's
// ConversationRenameRequest.title has no default, unlike create's) —
// this function doesn't pre-validate that itself, leaving it to the
// backend as the single source of truth, same as every other write in
// this API client.
export async function renameConversation(
  conversationId: string,
  title: string,
  options?: { signal?: AbortSignal }
): Promise<Conversation> {
  const conversation = await apiClient.patch<ConversationResponseWire>(
    `/conversations/${conversationId}`,
    { title },
    { signal: options?.signal }
  );
  return toConversation(conversation);
}

// DELETE /conversations/{id} — 204 No Content on success.
export async function deleteConversation(
  conversationId: string,
  options?: { signal?: AbortSignal }
): Promise<void> {
  await apiClient.delete<void>(`/conversations/${conversationId}`, {
    signal: options?.signal,
  });
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
