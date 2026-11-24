"use client";

import { useState } from "react";

export default function Home() {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"features" | "architecture" | "deployment">("features");

  const cloneCommand = "git clone https://github.com/your-username/kontexa.git";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cloneCommand);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is restricted
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="relative min-h-screen bg-slate-950 font-sans text-slate-100 selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Background ambient lighting */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute -top-40 left-1/2 h-[600px] w-[900px] -translate-x-1/2 rounded-full bg-gradient-to-tr from-indigo-600/15 via-purple-600/10 to-transparent blur-3xl" />
        <div className="absolute bottom-10 right-10 h-[500px] w-[600px] rounded-full bg-violet-600/10 blur-3xl" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 font-mono text-sm font-bold text-white shadow-lg shadow-indigo-500/25">
              K
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-white">Kontexa</span>
              <span className="ml-2 rounded-full bg-indigo-500/10 px-2 py-0.5 font-mono text-[10px] font-medium text-indigo-400 border border-indigo-500/20">
                v0.1.0
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              </span>
              <span>Vercel Deployment Live</span>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 mx-auto max-w-6xl px-6 pt-16 pb-24">
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/80 px-3.5 py-1 text-xs font-medium text-slate-300 shadow-inner backdrop-blur-sm">
            <span className="text-indigo-400">✦</span>
            <span>AI Workspace for Software Engineering</span>
          </div>

          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-white sm:text-6xl sm:leading-tight">
            Intelligent Context for{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-sky-400 bg-clip-text text-transparent">
              Modern Codebases
            </span>
          </h1>

          <p className="mt-5 text-base text-slate-400 sm:text-lg leading-relaxed">
            Kontexa unifies code architecture, semantic search, and project knowledge into an
            intelligent developer workspace. Built for deep comprehension and high-velocity shipping.
          </p>

          {/* Action CTAs */}
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleCopy}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:opacity-95 active:scale-[0.98] sm:w-auto cursor-pointer"
            >
              <span>{copied ? "Command Copied!" : "Clone Repository"}</span>
              <span className="font-mono text-xs opacity-75">
                {copied ? "✓" : "→"}
              </span>
            </button>

            <a
              href="https://vercel.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700/80 bg-slate-900/60 px-5 py-3 text-sm font-semibold text-slate-200 backdrop-blur-sm transition-colors hover:border-slate-600 hover:bg-slate-800/60 sm:w-auto"
            >
              <span>Deployed on Vercel</span>
              <span className="text-xs text-slate-400">↗</span>
            </a>
          </div>

          {/* Code pill */}
          <div className="mt-6 flex items-center justify-center">
            <div
              onClick={handleCopy}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  handleCopy();
                }
              }}
              role="button"
              tabIndex={0}
              className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/90 px-3.5 py-1.5 font-mono text-xs text-slate-400 hover:border-slate-700 hover:text-slate-200 transition-colors"
            >
              <span className="text-indigo-400">$</span>
              <span>{cloneCommand}</span>
              <span className="ml-1 text-[10px] text-slate-500">
                {copied ? "copied!" : "click to copy"}
              </span>
            </div>
          </div>
        </div>

        {/* Tab Selector */}
        <div className="mt-16 flex justify-center">
          <div className="inline-flex rounded-xl border border-slate-800 bg-slate-900/60 p-1 backdrop-blur-sm">
            {(
              [
                { id: "features", label: "Features" },
                { id: "architecture", label: "Architecture" },
                { id: "deployment", label: "Deployment Info" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`rounded-lg px-4 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === tab.id
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Tab Content */}
        <div className="mt-8">
          {activeTab === "features" && (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 backdrop-blur-sm transition-all hover:border-slate-700">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 mb-4 text-xl">
                  ⚡
                </div>
                <h2 className="text-base font-bold text-white">Context Graph & Retrieval</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">
                  Connect code symbols, AST definitions, and commit histories into a unified context
                  graph for high-precision retrieval and agentic reasoning.
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 backdrop-blur-sm transition-all hover:border-slate-700">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-400 mb-4 text-xl">
                  🛡️
                </div>
                <h2 className="text-base font-bold text-white">Modular Monolith</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">
                  Engineered with separation of concerns: Next.js frontend, FastAPI backend,
                  PostgreSQL with pgvector for embeddings, and Redis for caching.
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 backdrop-blur-sm transition-all hover:border-slate-700">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/10 text-sky-400 mb-4 text-xl">
                  🚀
                </div>
                <h2 className="text-base font-bold text-white">Production Vercel Ready</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">
                  Optimized for instant zero-config Vercel hosting. Zero external runtime blockers
                  when running frontend-only mode.
                </p>
              </div>
            </div>
          )}

          {activeTab === "architecture" && (
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-6 backdrop-blur-sm">
              <h2 className="text-base font-bold text-white mb-4">Repository Architecture Overview</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold text-indigo-400">frontend/</span>
                    <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Active</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                    Next.js 16 App Router with Turbopack, React 19, TypeScript, and Tailwind CSS v4. Deploys natively to Vercel.
                  </p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold text-violet-400">backend/</span>
                    <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded">Modular API</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                    FastAPI backend on Python 3.12+, managed via uv with Ruff linting and pytest test suites.
                  </p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold text-sky-400">infrastructure/</span>
                    <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded">Docker & DB</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                    PostgreSQL schemas with pgvector extensions, Redis cache configurations, and production Dockerfiles.
                  </p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold text-amber-400">docs/</span>
                    <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded">Specifications</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                    Detailed architecture designs, roadmap milestones, and engineering coding guidelines.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "deployment" && (
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-6 backdrop-blur-sm">
              <h2 className="text-base font-bold text-white mb-2">Vercel Deployment Status</h2>
              <p className="text-xs text-slate-400 mb-6">
                This frontend is built with static optimization and client hydration, ready to deploy via Vercel CLI or Git integration.
              </p>
              
              <div className="space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/80 px-4 py-2.5">
                  <span className="text-slate-400">Framework</span>
                  <span className="text-slate-200">Next.js 16.3.0</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/80 px-4 py-2.5">
                  <span className="text-slate-400">Rendering Engine</span>
                  <span className="text-slate-200">Turbopack (Static prerender)</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/80 px-4 py-2.5">
                  <span className="text-slate-400">Root Directory in Monorepo</span>
                  <span className="text-indigo-400 font-semibold">frontend</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/80 px-4 py-2.5">
                  <span className="text-slate-400">CLI Deployment Command</span>
                  <span className="text-emerald-400 font-semibold">cd frontend &amp;&amp; npx vercel</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-800/70 bg-slate-950/90 py-6 text-center text-xs text-slate-500">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 sm:flex-row">
          <span>&copy; {new Date().getFullYear()} Kontexa. All rights reserved.</span>
          <div className="flex gap-4">
            <span className="text-slate-400">Next.js 16</span>
            <span>·</span>
            <span className="text-slate-400">Tailwind CSS v4</span>
            <span>·</span>
            <span className="text-slate-400">Vercel Ready</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
