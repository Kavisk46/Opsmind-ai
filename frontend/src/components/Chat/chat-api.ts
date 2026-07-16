import { ApiClient } from "@/lib/api";

import type { Message } from "./types";

// Same-origin instance, separate from the app-wide `apiClient` singleton
// (that one targets the external backend at NEXT_PUBLIC_API_URL). The mock
// endpoint below lives inside this Next.js app, so this client's base URL
// is empty — relative paths resolve against the current origin.
const chatApiClient = new ApiClient("");

export function sendChatMessage(
  content: string
): Promise<{ message: Message }> {
  return chatApiClient.post<{ message: Message }>("/api/chat", { content });
}
