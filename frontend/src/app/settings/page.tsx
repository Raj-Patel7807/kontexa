"use client";

import * as React from "react";
import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUserApi, getCsrfTokenApi, UserProfile } from "../lib/auth";
import {
  listWorkspacesApi,
  createWorkspaceApi,
  updateWorkspaceApi,
  WorkspaceItem,
} from "../lib/workspaces";
import { AppShell } from "@/components/app-shell";
import { Button, Input, Modal, Badge, ErrorBoundary } from "@/components/ui";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [csrfToken, setCsrfToken] = useState<string>("");
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceItem | null>(null);

  // Settings form state
  const [wsName, setWsName] = useState("");
  const [wsSlug, setWsSlug] = useState("");
  const [isCreatingWs, setIsCreatingWs] = useState(false);
  const [newWsName, setNewWsName] = useState("");

  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        const userData = await getCurrentUserApi();
        if (!mounted) return;
        setUser(userData);

        const csrfData = await getCsrfTokenApi().catch(() => ({ csrf_token: "" }));
        if (mounted) setCsrfToken(csrfData.csrf_token);

        const wsList = await listWorkspacesApi();
        if (!mounted) return;
        setWorkspaces(wsList);

        if (wsList.length > 0) {
          setSelectedWorkspace(wsList[0]);
          setWsName(wsList[0].name);
          setWsSlug(wsList[0].slug);
        }
      } catch {
        router.push("/login");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
    };
  }, [router]);

  const handleSelectWorkspace = (ws: WorkspaceItem) => {
    setSelectedWorkspace(ws);
    setWsName(ws.name);
    setWsSlug(ws.slug);
    setFeedback(null);
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace) return;
    setFeedback(null);

    startTransition(async () => {
      try {
        const updated = await updateWorkspaceApi(
          selectedWorkspace.id,
          {
            name: wsName.trim() || undefined,
            slug: wsSlug.trim() || undefined,
          },
          csrfToken
        );
        setSelectedWorkspace(updated);
        setWorkspaces((prev) =>
          prev.map((w) => (w.id === updated.id ? updated : w))
        );
        setFeedback({ type: "success", message: "Workspace settings updated successfully." });
      } catch (err: unknown) {
        setFeedback({
          type: "error",
          message: err instanceof Error ? err.message : "Failed to update workspace settings.",
        });
      }
    });
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;

    startTransition(async () => {
      try {
        const created = await createWorkspaceApi(newWsName.trim(), undefined, csrfToken);
        setWorkspaces((prev) => [created, ...prev]);
        handleSelectWorkspace(created);
        setNewWsName("");
        setIsCreatingWs(false);
        setFeedback({ type: "success", message: `Workspace '${created.name}' created.` });
      } catch (err: unknown) {
        setFeedback({
          type: "error",
          message: err instanceof Error ? err.message : "Failed to create workspace.",
        });
      }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        Loading settings...
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const isOwnerOrAdmin =
    selectedWorkspace?.current_user_role === "owner" ||
    selectedWorkspace?.current_user_role === "admin";

  return (
    <ErrorBoundary>
      <AppShell
        user={user}
        workspaces={workspaces}
        currentWorkspace={selectedWorkspace}
        onSelectWorkspace={handleSelectWorkspace}
        onOpenCreateWorkspace={() => setIsCreatingWs(true)}
        csrfToken={csrfToken}
      >
        <div className="p-6 max-w-4xl w-full mx-auto space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold text-white">Organization Settings</h1>
              <p className="text-xs text-slate-400 mt-1">
                Manage workspace details, role permissions, and organization identifiers.
              </p>
            </div>
            {selectedWorkspace && (
              <Badge variant="info">
                Role: {selectedWorkspace.current_user_role}
              </Badge>
            )}
          </div>

          {feedback && (
            <div
              className={`p-3 rounded-lg text-xs font-medium border ${
                feedback.type === "success"
                  ? "bg-emerald-950/60 border-emerald-800/60 text-emerald-300"
                  : "bg-rose-950/60 border-rose-800/60 text-rose-300"
              }`}
            >
              {feedback.message}
            </div>
          )}

          {selectedWorkspace ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
              <form onSubmit={handleSaveSettings} className="space-y-4">
                <Input
                  label="Workspace Name"
                  value={wsName}
                  disabled={!isOwnerOrAdmin || isPending}
                  onChange={(e) => setWsName(e.target.value)}
                  helperText="Human-readable name of your organization."
                />

                <Input
                  label="URL Slug"
                  value={wsSlug}
                  disabled={!isOwnerOrAdmin || isPending}
                  onChange={(e) => setWsSlug(e.target.value)}
                  helperText="Unique identifier used in URLs and API routes."
                />

                <div className="pt-2 flex items-center justify-between">
                  <span className="text-xs text-slate-500">
                    {!isOwnerOrAdmin && "Admin or Owner permissions required to edit settings."}
                  </span>
                  {isOwnerOrAdmin && (
                    <Button type="submit" size="sm" isLoading={isPending}>
                      Save Changes
                    </Button>
                  )}
                </div>
              </form>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500">
              No workspace selected. Select or create a workspace to view its settings.
            </div>
          )}
        </div>

        <Modal
          isOpen={isCreatingWs}
          onClose={() => setIsCreatingWs(false)}
          title="Create Workspace"
          description="Organizations isolate repositories, documents, and chat contexts."
        >
          <form onSubmit={handleCreateWorkspace} className="space-y-4">
            <Input
              label="Organization Name"
              required
              placeholder="e.g. Acme Engineering"
              value={newWsName}
              onChange={(e) => setNewWsName(e.target.value)}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsCreatingWs(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" isLoading={isPending}>
                Create Organization
              </Button>
            </div>
          </form>
        </Modal>
      </AppShell>
    </ErrorBoundary>
  );
}
