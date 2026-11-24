/**
 * Authentication type definitions and API client functions.
 * Browser credentials are sent as HttpOnly cookies (credentials: "include").
 */

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface WorkspaceSummary {
  workspace_id: string;
  name: string;
  slug: string;
  role: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
  is_active: boolean;
  created_at: string;
  workspaces: WorkspaceSummary[];
}

export interface AuthSession {
  user: UserProfile;
  active_workspace_id?: string | null;
  csrf_token: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function registerApi(payload: {
  email: string;
  password: string;
  name: string;
}): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Registration failed." }));
    throw new Error(errorData.detail || "Registration failed.");
  }

  return res.json();
}

export async function loginApi(payload: {
  email: string;
  password: string;
}): Promise<AuthSession> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Invalid email or password." }));
    throw new Error(errorData.detail || "Invalid email or password.");
  }

  return res.json();
}

export async function getCurrentUserApi(): Promise<CurrentUser> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    method: "GET",
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error("Unauthorized");
  }

  return res.json();
}

export async function logoutApi(csrfToken?: string): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  await fetch(`${API_BASE}/api/v1/auth/logout`, {
    method: "POST",
    headers,
    credentials: "include",
  });
}
