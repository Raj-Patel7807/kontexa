/**
 * Workspace and Project API client functions for Kontexa.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface WorkspaceItem {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
  current_user_role: string;
  member_count?: number;
}

export interface WorkspaceMember {
  workspace_id: string;
  user_id: string;
  email: string;
  name: string | null;
  role: string;
}

export interface ProjectItem {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export async function listWorkspacesApi(): Promise<WorkspaceItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch workspaces: ${res.status}`);
  }
  return res.json();
}

export async function createWorkspaceApi(
  name: string,
  slug?: string,
  csrfToken?: string
): Promise<WorkspaceItem> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({ name, slug: slug || undefined }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create workspace: ${res.status}`);
  }
  return res.json();
}

export async function getWorkspaceApi(workspaceId: string): Promise<WorkspaceItem> {
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch workspace: ${res.status}`);
  }
  return res.json();
}

export async function updateWorkspaceApi(
  workspaceId: string,
  data: { name?: string; slug?: string },
  csrfToken?: string
): Promise<WorkspaceItem> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}`, {
    method: "PATCH",
    credentials: "include",
    headers,
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update workspace: ${res.status}`);
  }
  return res.json();
}

export async function listMembersApi(workspaceId: string): Promise<WorkspaceMember[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}/members`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch members: ${res.status}`);
  }
  return res.json();
}

export async function addMemberApi(
  workspaceId: string,
  email: string,
  role: string,
  csrfToken?: string
): Promise<WorkspaceMember> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}/members`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({ email, role }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to add member: ${res.status}`);
  }
  return res.json();
}

export async function listProjectsApi(workspaceId: string): Promise<ProjectItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}/projects`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch projects: ${res.status}`);
  }
  return res.json();
}

export async function createProjectApi(
  workspaceId: string,
  name: string,
  slug?: string,
  description?: string,
  csrfToken?: string
): Promise<ProjectItem> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const res = await fetch(`${API_BASE_URL}/api/v1/workspaces/${workspaceId}/projects`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({
      name,
      slug: slug || undefined,
      description: description || undefined,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create project: ${res.status}`);
  }
  return res.json();
}
