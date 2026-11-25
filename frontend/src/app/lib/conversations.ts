/**
 * Conversation and Message API client functions for Kontexa.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ConversationItem {
  id: string;
  workspace_id: string;
  project_id: string | null;
  title: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageItem {
  id: string;
  conversation_id: string;
  user_id: string | null;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

export async function listConversationsApi(
  workspaceId: string,
  projectId?: string
): Promise<ConversationItem[]> {
  const url = new URL(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}/conversations`);
  if (projectId) {
    url.searchParams.set("project_id", projectId);
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch conversations: ${res.status}`);
  }
  return res.json();
}

export async function createConversationApi(
  workspaceId: string,
  projectId?: string,
  title?: string,
  csrfToken?: string
): Promise<ConversationItem> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}/conversations`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({
      project_id: projectId || undefined,
      title: title || undefined,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create conversation: ${res.status}`);
  }
  return res.json();
}

export async function renameConversationApi(
  workspaceId: string,
  conversationId: string,
  title: string,
  csrfToken?: string
): Promise<ConversationItem> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const res = await fetch(
    `${API_BASE_URL}/api/v1/workspaces/${workspaceId}/conversations/${conversationId}`,
    {
      method: "PATCH",
      credentials: "include",
      headers,
      body: JSON.stringify({ title }),
    }
  );

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to rename conversation: ${res.status}`);
  }
  return res.json();
}

export async function deleteConversationApi(
  workspaceId: string,
  conversationId: string,
  csrfToken?: string
): Promise<void> {
  const headers: Record<string, string> = {};
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const res = await fetch(
    `${API_BASE_URL}/api/v1/workspaces/${workspaceId}/conversations/${conversationId}`,
    {
      method: "DELETE",
      credentials: "include",
      headers,
    }
  );

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete conversation: ${res.status}`);
  }
}

export async function listMessagesApi(
  workspaceId: string,
  conversationId: string
): Promise<MessageItem[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/workspaces/${workspaceId}/conversations/${conversationId}/messages`,
    {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    }
  );

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch messages: ${res.status}`);
  }
  return res.json();
}

export async function sendMessageApi(
  workspaceId: string,
  conversationId: string,
  content: string,
  idempotencyKey?: string,
  csrfToken?: string
): Promise<MessageItem[]> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const res = await fetch(
    `${API_BASE_URL}/api/v1/workspaces/${workspaceId}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify({
        content,
        idempotency_key: idempotencyKey || undefined,
      }),
    }
  );

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to send message: ${res.status}`);
  }
  return res.json();
}
