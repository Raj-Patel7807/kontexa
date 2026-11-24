"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CurrentUser, getCurrentUserApi, logoutApi } from "../lib/auth";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    getCurrentUserApi()
      .then((data) => {
        if (mounted) {
          setUser(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) {
          router.push("/login");
        }
      });

    return () => {
      mounted = false;
    };
  }, [router]);

  const handleLogout = async () => {
    try {
      await logoutApi();
      router.push("/login");
    } catch {
      setError("Failed to sign out.");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent"></div>
          <p className="mt-3 text-sm">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Top navigation bar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-3">
            <Link href="/dashboard" className="text-xl font-bold tracking-tight text-white">
              Kontexa<span className="text-cyan-400">.</span>
            </Link>
            <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
              Workspace
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-sm font-medium text-slate-200">{user.name}</p>
              <p className="text-xs text-slate-400">{user.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-slate-700 hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main dashboard content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 rounded-md border border-red-500/30 bg-red-950/40 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-3">
          {/* Identity card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 shadow-sm">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Authenticated Account
            </h3>
            <div className="mt-4 space-y-2">
              <p className="text-lg font-medium text-slate-100">{user.name}</p>
              <p className="text-sm text-slate-400">{user.email}</p>
              <span className="inline-flex items-center rounded-full bg-emerald-950/80 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-800/40">
                Active Session
              </span>
            </div>
          </div>

          {/* Workspaces card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 shadow-sm md:col-span-2">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Workspace Memberships
            </h3>
            {user.workspaces.length === 0 ? (
              <div className="mt-4 rounded-lg border border-dashed border-slate-800 p-6 text-center text-sm text-slate-500">
                No active workspace memberships found. Create or join a workspace in Sprint 08.
              </div>
            ) : (
              <ul className="mt-4 divide-y divide-slate-800">
                {user.workspaces.map((ws) => (
                  <li key={ws.workspace_id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-medium text-slate-200">{ws.name}</p>
                      <p className="text-xs text-slate-500">/{ws.slug}</p>
                    </div>
                    <span className="rounded bg-cyan-950/80 px-2 py-0.5 text-xs font-medium text-cyan-400 border border-cyan-800/40">
                      {ws.role}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
