"use client";

import * as React from "react";
import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUserApi, getCsrfTokenApi, UserProfile } from "../lib/auth";
import {
  listWorkspacesApi,
  createWorkspaceApi,
  listProjectsApi,
  createProjectApi,
  listMembersApi,
  addMemberApi,
  WorkspaceItem,
  ProjectItem,
  WorkspaceMember,
} from "../lib/workspaces";
import { AppShell } from "@/components/app-shell";
import {
  Button,
  Input,
  Modal,
  Badge,
  EmptyState,
  ErrorBoundary,
  DashboardSkeleton,
} from "@/components/ui";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [csrfToken, setCsrfToken] = useState<string>("");
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceItem | null>(null);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);

  // Modal / Form state
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newPrjName, setNewPrjName] = useState("");
  const [newPrjDesc, setNewPrjDesc] = useState("");
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberRole, setNewMemberRole] = useState("member");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // Load initial user and workspaces
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

  // When selected workspace changes, load its projects and members
  useEffect(() => {
    if (!selectedWorkspace) return;

    let mounted = true;
    async function loadWorkspaceDetails(wsId: string) {
      try {
        const [prjList, memList] = await Promise.all([
          listProjectsApi(wsId),
          listMembersApi(wsId),
        ]);
        if (!mounted) return;
        setProjects(prjList);
        setMembers(memList);
      } catch (err: unknown) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Failed to load workspace data");
      }
    }
    loadWorkspaceDetails(selectedWorkspace.id);
    return () => {
      mounted = false;
    };
  }, [selectedWorkspace]);

  const handleSelectWorkspace = (ws: WorkspaceItem) => {
    setProjects([]);
    setMembers([]);
    setSelectedWorkspace(ws);
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    setError(null);

    startTransition(async () => {
      try {
        const created = await createWorkspaceApi(newWsName.trim(), undefined, csrfToken);
        setWorkspaces((prev) => [created, ...prev]);
        setSelectedWorkspace(created);
        setProjects([]);
        setMembers([]);
        setNewWsName("");
        setIsCreatingWorkspace(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to create workspace");
      }
    });
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace || !newPrjName.trim()) return;
    setError(null);

    startTransition(async () => {
      try {
        const created = await createProjectApi(
          selectedWorkspace.id,
          newPrjName.trim(),
          undefined,
          newPrjDesc.trim() || undefined,
          csrfToken
        );
        setProjects((prev) => [created, ...prev]);
        setNewPrjName("");
        setNewPrjDesc("");
        setIsCreatingProject(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to create project");
      }
    });
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace || !newMemberEmail.trim()) return;
    setError(null);

    startTransition(async () => {
      try {
        const member = await addMemberApi(
          selectedWorkspace.id,
          newMemberEmail.trim(),
          newMemberRole,
          csrfToken
        );
        setMembers((prev) => [...prev, member]);
        setNewMemberEmail("");
        setIsAddingMember(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to add member");
      }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col justify-center">
        <DashboardSkeleton />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <ErrorBoundary>
      <AppShell
        user={user}
        workspaces={workspaces}
        currentWorkspace={selectedWorkspace}
        onSelectWorkspace={handleSelectWorkspace}
        onOpenCreateWorkspace={() => setIsCreatingWorkspace(true)}
        csrfToken={csrfToken}
      >
        <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
          {/* Top Bar / Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold text-white tracking-tight">
                  {selectedWorkspace ? selectedWorkspace.name : "Select an Organization"}
                </h1>
                {selectedWorkspace && (
                  <Badge variant="info">
                    {selectedWorkspace.current_user_role}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                {selectedWorkspace ? `Slug: ${selectedWorkspace.slug}` : "Create or pick a workspace to get started"}
              </p>
            </div>

            {selectedWorkspace && (
              <Button size="sm" onClick={() => setIsCreatingProject(true)}>
                + New Project
              </Button>
            )}
          </div>

          {error && (
            <div className="p-3 bg-rose-950/50 border border-rose-800/60 rounded-lg text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          {/* Grid Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Projects */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                  Projects ({projects.length})
                </h2>
              </div>

              {projects.length === 0 ? (
                <EmptyState
                  title="No projects in this organization"
                  description="Projects containerize repositories, documents, and task plans with strict workspace isolation."
                  actionLabel={selectedWorkspace ? "Create First Project" : undefined}
                  onAction={() => setIsCreatingProject(true)}
                />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {projects.map((prj) => (
                    <div
                      key={prj.id}
                      className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl hover:border-slate-700 hover:bg-slate-900/90 transition-all flex flex-col justify-between group shadow-sm"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
                            {prj.name}
                          </h3>
                          <Badge variant="success">{prj.status}</Badge>
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">
                          {prj.description || "No project description provided."}
                        </p>
                      </div>
                      <div className="flex items-center justify-between pt-3 border-t border-slate-800/60 text-[11px] font-mono text-slate-500">
                        <span>{prj.slug}</span>
                        <span>{new Date(prj.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right Col: Team Members */}
            <div className="space-y-4">
              <div className="p-5 bg-slate-900/50 border border-slate-800 rounded-xl">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Team Members ({members.length})
                  </h2>
                  {selectedWorkspace && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setIsAddingMember(true)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 p-0 h-auto"
                    >
                      + Add
                    </Button>
                  )}
                </div>

                <div className="divide-y divide-slate-800/60">
                  {members.length === 0 ? (
                    <p className="text-xs text-slate-500 py-2">No members loaded.</p>
                  ) : (
                    members.map((mem) => (
                      <div key={mem.user_id} className="py-2.5 flex items-center justify-between gap-2">
                        <div className="overflow-hidden">
                          <p className="text-xs font-medium text-slate-200 truncate">{mem.name || mem.email}</p>
                          <p className="text-[10px] text-slate-500 truncate">{mem.email}</p>
                        </div>
                        <Badge variant="default">{mem.role}</Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal: Create Workspace */}
        <Modal
          isOpen={isCreatingWorkspace}
          onClose={() => setIsCreatingWorkspace(false)}
          title="Create Organization"
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
                onClick={() => setIsCreatingWorkspace(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" isLoading={isPending}>
                Create Organization
              </Button>
            </div>
          </form>
        </Modal>

        {/* Modal: Create Project */}
        <Modal
          isOpen={isCreatingProject}
          onClose={() => setIsCreatingProject(false)}
          title="Create Project"
          description="Projects group codebases, conversations, and task plans within this workspace."
        >
          <form onSubmit={handleCreateProject} className="space-y-4">
            <Input
              label="Project Name"
              required
              placeholder="e.g. Backend API Gateway"
              value={newPrjName}
              onChange={(e) => setNewPrjName(e.target.value)}
            />
            <div className="flex flex-col gap-1.5 text-left">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Description (Optional)
              </label>
              <textarea
                rows={3}
                placeholder="High-level goal or repository focus"
                value={newPrjDesc}
                onChange={(e) => setNewPrjDesc(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-950 transition-colors"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsCreatingProject(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" isLoading={isPending}>
                Create Project
              </Button>
            </div>
          </form>
        </Modal>

        {/* Modal: Add Member */}
        <Modal
          isOpen={isAddingMember}
          onClose={() => setIsAddingMember(false)}
          title="Add Team Member"
          description="Grant a registered Kontexa user access to collaborate in this workspace."
        >
          <form onSubmit={handleAddMember} className="space-y-4">
            <Input
              label="User Email"
              type="email"
              required
              placeholder="teammate@example.com"
              value={newMemberEmail}
              onChange={(e) => setNewMemberEmail(e.target.value)}
            />
            <div className="flex flex-col gap-1.5 text-left">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Role Assignment
              </label>
              <select
                value={newMemberRole}
                onChange={(e) => setNewMemberRole(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 transition-colors"
              >
                <option value="member">Member (Can create/edit projects & chats)</option>
                <option value="admin">Admin (Can manage settings & invite members)</option>
                <option value="viewer">Viewer (Read-only access)</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsAddingMember(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" isLoading={isPending}>
                Add Member
              </Button>
            </div>
          </form>
        </Modal>
      </AppShell>
    </ErrorBoundary>
  );
}
