import { listConversations } from "@/components/Chat/chat-api";
import { listDocuments } from "@/components/KnowledgeBase/documents-api";

// There is no dedicated activity-log endpoint anywhere in the backend
// (verified: no such route exists in api/routes/). This assembles a real
// feed from two things that DO exist and that each carry a genuine
// timestamp: document uploads (GET /documents' created_at) and
// conversations (GET /conversations' updated_at, which the backend bumps
// on every new message — see ConversationRepository.list_by_owner's
// comment). Every document/conversation here belongs to the current user
// (both endpoints are owner-scoped), so "actor" is always "You" — this
// backend has no concept of OTHER users' activity to show.
export interface ActivityEntry {
  id: string;
  actor: string;
  action: string;
  target: string;
  type: "Upload" | "AI";
  timestamp: string;
}

const MAX_ENTRIES = 10;

export async function listRecentActivity(options?: {
  signal?: AbortSignal;
}): Promise<ActivityEntry[]> {
  const [documents, conversations] = await Promise.all([
    listDocuments({ signal: options?.signal }),
    listConversations({ signal: options?.signal }),
  ]);

  const uploadEntries: ActivityEntry[] = documents.map((document) => ({
    id: `document:${document.id}`,
    actor: "You",
    action: "uploaded",
    target: document.filename,
    type: "Upload",
    timestamp: document.createdAt,
  }));

  const conversationEntries: ActivityEntry[] = conversations.map(
    (conversation) => ({
      id: `conversation:${conversation.id}`,
      actor: "You",
      action: "chatted in",
      target: conversation.title,
      type: "AI",
      timestamp: conversation.updatedAt,
    })
  );

  return [...uploadEntries, ...conversationEntries]
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .slice(0, MAX_ENTRIES);
}
