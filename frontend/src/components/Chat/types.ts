export type MessageRole = "user" | "assistant";

export interface Citation {
  documentId: string;
  documentName: string;
  chunkIndex: number;
  pageNumber: number | null;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  // Only ever present on a completed assistant reply from the real backend
  // (see chat-api.ts) — absent on user messages, on mock seed history, and
  // on an assistant message that's still streaming (citations only arrive
  // in the stream's final "done" event, after all delta chunks).
  citations?: Citation[];
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
  lastMessagePreview: string;
  isPinned: boolean;
  messageCount: number;
}
