"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { UserProfile, logoutApi } from "@/app/lib/auth";
import { WorkspaceItem } from "@/app/lib/workspaces";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export interface AppShellProps {
  user: UserProfile;
  workspaces: WorkspaceItem[];
  currentWorkspace: WorkspaceItem | null;
  onSelectWorkspace: (workspace: WorkspaceItem) => void;
  onOpenCreateWorkspace: () => void;
  csrfToken: string;
  children: React.ReactNode;
}

export function AppShell({
  user,
  workspaces,
  currentWorkspace,
  onSelectWorkspace,
  onOpenCreateWorkspace,
  csrfToken,
  children,
}: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [userMenuOpen, setUserMenuOpen] = React.useState(false);

  const handleLogout = async () => {
    try {
      await logoutApi(csrfToken);
      router.push("/login");
    } catch {
      router.push("/login");
    }
  };

  const navLinks = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      name: "Settings",
      href: "/settings",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-slate-950 text-slate-100">
      {/* Mobile Top Header */}
      <div className="md:hidden flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
        <Link href="/dashboard" className="text-base font-bold text-white flex items-center gap-2">
          <span className="h-6 w-6 rounded bg-indigo-600 flex items-center justify-center font-mono text-xs">K</span>
          Kontexa
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          aria-label="Toggle navigation"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={mobileMenuOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
          </svg>
        </button>
      </div>

      {/* Sidebar Navigation */}
      <aside
        className={`${
          mobileMenuOpen ? "block" : "hidden"
        } md:flex flex-col w-full md:w-64 bg-slate-900/90 border-r border-slate-800/80 shrink-0 select-none z-20`}
      >
        {/* Brand Header */}
        <div className="hidden md:flex items-center gap-3 px-5 py-4 border-b border-slate-800/80">
          <div className="h-7 w-7 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-sm font-mono text-sm">
            K
          </div>
          <div>
            <h1 className="text-sm font-bold text-white leading-none">Kontexa</h1>
            <span className="text-[10px] text-slate-400 font-mono">Workspace Core</span>
          </div>
        </div>

        {/* Workspace Switcher Selector */}
        <div className="px-4 py-3 border-b border-slate-800/60">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5 block">
            Organization
          </label>
          <div className="flex items-center gap-1.5">
            <select
              value={currentWorkspace?.id || ""}
              onChange={(e) => {
                const found = workspaces.find((w) => w.id === e.target.value);
                if (found) onSelectWorkspace(found);
              }}
              className="w-full bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 transition-colors"
            >
              {workspaces.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name} ({ws.current_user_role})
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="outline"
              onClick={onOpenCreateWorkspace}
              title="Create new workspace"
              className="px-2 py-1.5 text-xs text-indigo-400 hover:text-indigo-300"
            >
              +
            </Button>
          </div>
        </div>

        {/* Primary Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navLinks.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                }`}
              >
                {item.icon}
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User Account Section */}
        <div className="p-3 border-t border-slate-800/80">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/80 transition-colors text-left"
            >
              <div className="flex items-center gap-2.5 overflow-hidden">
                <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-indigo-400 shrink-0">
                  {user.name ? user.name[0].toUpperCase() : user.email[0].toUpperCase()}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-medium text-slate-200 truncate">{user.name || user.email}</p>
                  <p className="text-[10px] text-slate-400 truncate">{user.email}</p>
                </div>
              </div>
              <svg className="w-4 h-4 text-slate-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {userMenuOpen && (
              <div className="absolute bottom-full left-0 mb-1 w-full rounded-lg bg-slate-900 border border-slate-800 p-1 shadow-xl z-30">
                <div className="px-3 py-2 border-b border-slate-800/60 text-xs">
                  <span className="text-slate-400 block text-[10px]">Active Role</span>
                  <Badge variant="info" className="mt-1">
                    {currentWorkspace?.current_user_role || "User"}
                  </Badge>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-xs text-rose-400 hover:bg-rose-950/40 rounded transition-colors"
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Pane */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
