"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getCurrentUserApi, logoutApi, getCsrfTokenApi, UserProfile } from "../lib/auth";
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
      } catch (err: unknown) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Failed to load session");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

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

  const handleWorkspaceChange = (wsId: string) => {
    const ws = workspaces.find((w) => w.id === wsId);
    if (ws) {
      setProjects([]);
      setMembers([]);
      setSelectedWorkspace(ws);
    }
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

  const handleLogout = async () => {
    try {
      await logoutApi(csrfToken);
      router.push("/login");
    } catch {
      router.push("/login");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        Loading workspace session...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
        <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-slate-400 mb-6">You must be logged in to access this workspace.</p>
        <Link
          href="/login"
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium"
        >
          Return to Sign In
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/60 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link href="/dashboard" className="text-lg font-bold tracking-tight text-white">
            Kontexa <span className="text-xs font-normal text-indigo-400 px-2 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/50">Core</span>
          </Link>

          {/* Workspace Switcher */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Workspace:</span>
            <select
              value={selectedWorkspace?.id || ""}
              onChange={(e) => handleWorkspaceChange(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white text-sm rounded px-3 py-1 focus:outline-none focus:border-indigo-500"
            >
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name} ({ws.current_user_role})
                </option>
              ))}
            </select>
            <button
              onClick={() => setIsCreatingWorkspace(true)}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium px-2 py-1 rounded hover:bg-slate-800"
            >
              + New
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-sm">
          <span className="text-slate-400">{user.email}</span>
          <button
            onClick={handleLogout}
            className="px-3 py-1 rounded text-xs font-medium bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-200 border border-slate-700"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto p-6 gap-6">
        {/* Left: Projects Column */}
        <section className="w-2/3 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">
                {selectedWorkspace ? selectedWorkspace.name : "No Workspace Selected"}
              </h2>
              <p className="text-xs text-slate-400">
                Slug: <code className="text-indigo-400 font-mono">{selectedWorkspace?.slug}</code> • Role: <span className="font-semibold text-slate-300">{selectedWorkspace?.current_user_role}</span>
              </p>
            </div>
            {selectedWorkspace && (
              <button
                onClick={() => setIsCreatingProject(true)}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded shadow transition"
              >
                + New Project
              </button>
            )}
          </div>

          {error && (
            <div className="p-3 bg-rose-950/50 border border-rose-800/60 rounded text-rose-300 text-sm">
              {error}
            </div>
          )}

          {/* Project Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
            {projects.length === 0 ? (
              <div className="col-span-2 p-8 border border-dashed border-slate-800 rounded-lg text-center text-slate-500 text-sm">
                No projects yet in this workspace. Create your first project to organize repositories, documents, and chat threads.
              </div>
            ) : (
              projects.map((prj) => (
                <div
                  key={prj.id}
                  className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg hover:border-slate-700 transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="font-semibold text-white">{prj.name}</h3>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/50">
                        {prj.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                      {prj.description || "No description provided."}
                    </p>
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    slug: {prj.slug}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Right: Members & Workspace Info */}
        <aside className="w-1/3 flex flex-col gap-4">
          <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Members ({members.length})</h3>
              {selectedWorkspace && (
                <button
                  onClick={() => setIsAddingMember(true)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  + Add Member
                </button>
              )}
            </div>

            <div className="divide-y divide-slate-800/60 text-sm">
              {members.map((mem) => (
                <div key={mem.user_id} className="py-2.5 flex items-center justify-between">
                  <div className="overflow-hidden mr-2">
                    <p className="font-medium text-slate-200 truncate">{mem.name || mem.email}</p>
                    <p className="text-xs text-slate-500 truncate">{mem.email}</p>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 capitalize">
                    {mem.role}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>

      {/* Modal: Create Workspace */}
      {isCreatingWorkspace && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleCreateWorkspace}
            className="bg-slate-900 border border-slate-800 rounded-lg max-w-md w-full p-6 shadow-xl"
          >
            <h3 className="text-lg font-bold text-white mb-2">Create Workspace</h3>
            <p className="text-xs text-slate-400 mb-4">
              Workspaces isolate repositories, documents, and chat contexts between organizations.
            </p>
            <input
              type="text"
              required
              placeholder="e.g. Acme Engineering"
              value={newWsName}
              onChange={(e) => setNewWsName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-white mb-4 focus:outline-none focus:border-indigo-500"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsCreatingWorkspace(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded"
              >
                {isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal: Create Project */}
      {isCreatingProject && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleCreateProject}
            className="bg-slate-900 border border-slate-800 rounded-lg max-w-md w-full p-6 shadow-xl"
          >
            <h3 className="text-lg font-bold text-white mb-2">Create Project</h3>
            <p className="text-xs text-slate-400 mb-4">
              Projects group codebases, conversations, and task plans within this workspace.
            </p>
            <div className="flex flex-col gap-3 mb-4">
              <input
                type="text"
                required
                placeholder="Project Name (e.g. Backend API Service)"
                value={newPrjName}
                onChange={(e) => setNewPrjName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
              <textarea
                placeholder="Optional description"
                rows={3}
                value={newPrjDesc}
                onChange={(e) => setNewPrjDesc(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsCreatingProject(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded"
              >
                {isPending ? "Creating..." : "Create Project"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal: Add Member */}
      {isAddingMember && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleAddMember}
            className="bg-slate-900 border border-slate-800 rounded-lg max-w-md w-full p-6 shadow-xl"
          >
            <h3 className="text-lg font-bold text-white mb-2">Add Member</h3>
            <p className="text-xs text-slate-400 mb-4">
              Add a registered Kontexa user to collaborate in this workspace.
            </p>
            <div className="flex flex-col gap-3 mb-4">
              <input
                type="email"
                required
                placeholder="teammate@example.com"
                value={newMemberEmail}
                onChange={(e) => setNewMemberEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
              <select
                value={newMemberRole}
                onChange={(e) => setNewMemberRole(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="member">Member (Can create/edit projects & chats)</option>
                <option value="admin">Admin (Can manage settings & invite members)</option>
                <option value="viewer">Viewer (Read-only access)</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsAddingMember(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded"
              >
                {isPending ? "Adding..." : "Add Member"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
