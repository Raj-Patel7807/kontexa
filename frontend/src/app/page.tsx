"use client";

import { useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ServiceStatus = "ok" | "unavailable";

type DependencyHealth = {
  status: ServiceStatus;
  latency_ms: number;
};

type HealthResponse = {
  status: "ok" | "degraded";
  service: string;
  environment: string;
  version: string;
  timestamp: string;
  dependencies: {
    database: DependencyHealth;
    redis: DependencyHealth;
  };
};

type HealthState =
  | { kind: "checking" }
  | { kind: "available"; health: HealthResponse; checkedAt: Date }
  | { kind: "unavailable"; checkedAt: Date };

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 15_000;

// ---------------------------------------------------------------------------
// Service card descriptors
// ---------------------------------------------------------------------------

type ServiceDescriptor = {
  id: string;
  label: string;
  description: string;
  icon: string;
  getStatus: (health: HealthResponse) => ServiceStatus;
  getLatency: (health: HealthResponse) => number | null;
};

const SERVICES: ServiceDescriptor[] = [
  {
    id: "backend",
    label: "Backend API",
    description: "FastAPI · Python 3.12+",
    icon: "⬡",
    getStatus: (h) => h.status === "ok" ? "ok" : "unavailable",
    getLatency: () => null,
  },
  {
    id: "database",
    label: "PostgreSQL",
    description: "pgvector · Primary data store",
    icon: "◈",
    getStatus: (h) => h.dependencies.database.status,
    getLatency: (h) => h.dependencies.database.latency_ms,
  },
  {
    id: "redis",
    label: "Redis",
    description: "Session cache · Rate limiting",
    icon: "◎",
    getStatus: (h) => h.dependencies.redis.status,
    getLatency: (h) => h.dependencies.redis.latency_ms,
  },
];

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function formatLatency(ms: number): string {
  return ms < 1 ? "<1 ms" : `${ms.toFixed(1)} ms`;
}

function formatCheckedAt(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

// ---------------------------------------------------------------------------
// Guard
// ---------------------------------------------------------------------------

function isRecord(data: unknown): data is Record<string, unknown> {
  return typeof data === "object" && data !== null;
}

function isDependencyHealth(data: unknown): data is DependencyHealth {
  return (
    isRecord(data) &&
    (data.status === "ok" || data.status === "unavailable") &&
    typeof data.latency_ms === "number"
  );
}

function isHealthResponse(data: unknown): data is HealthResponse {
  if (!isRecord(data) || !isRecord(data.dependencies)) return false;
  return (
    (data.status === "ok" || data.status === "degraded") &&
    typeof data.service === "string" &&
    typeof data.environment === "string" &&
    typeof data.version === "string" &&
    typeof data.timestamp === "string" &&
    isDependencyHealth(data.dependencies.database) &&
    isDependencyHealth(data.dependencies.redis)
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusDot({ status }: { status: ServiceStatus }) {
  if (status === "ok") {
    return (
      <span className="relative flex h-2.5 w-2.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
      </span>
    );
  }
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
    </span>
  );
}

function StatusBadge({ status }: { status: "ok" | "degraded" | "unavailable" }) {
  const styles: Record<string, string> = {
    ok: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
    degraded: "bg-amber-500/10 text-amber-400 border-amber-500/25",
    unavailable: "bg-red-500/10 text-red-400 border-red-500/25",
  };
  const labels: Record<string, string> = {
    ok: "Operational",
    degraded: "Degraded",
    unavailable: "Unavailable",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status === "ok" && <StatusDot status="ok" />}
      {status === "degraded" && <span className="h-2.5 w-2.5 rounded-full bg-amber-400 animate-pulse inline-block" />}
      {status === "unavailable" && <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />}
      {labels[status]}
    </span>
  );
}

function ServiceCard({
  service,
  health,
}: {
  service: ServiceDescriptor;
  health: HealthResponse;
}) {
  const serviceStatus = service.getStatus(health);
  const latency = service.getLatency(health);

  const borderColor =
    serviceStatus === "ok"
      ? "border-slate-700/60 hover:border-emerald-500/30"
      : "border-red-500/30";

  const iconColor =
    service.id === "backend"
      ? "text-indigo-400"
      : service.id === "database"
      ? "text-violet-400"
      : "text-sky-400";

  return (
    <div
      className={`relative flex flex-col gap-4 rounded-2xl border bg-slate-900/60 p-5 backdrop-blur-sm transition-colors duration-300 ${borderColor}`}
    >
      {/* Top row */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800/80 text-xl font-light ${iconColor}`}
            aria-hidden="true"
          >
            {service.icon}
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">{service.label}</p>
            <p className="text-xs text-slate-500">{service.description}</p>
          </div>
        </div>
        <StatusDot status={serviceStatus} />
      </div>

      {/* Bottom row */}
      <div className="flex items-center justify-between border-t border-slate-800/60 pt-3">
        <span
          className={`text-xs font-medium ${
            serviceStatus === "ok" ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {serviceStatus === "ok" ? "Online" : "Offline"}
        </span>
        {latency !== null && (
          <span className="font-mono text-xs text-slate-500">
            {formatLatency(latency)}
          </span>
        )}
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-800/50 bg-slate-900/40 p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 animate-pulse rounded-xl bg-slate-800" />
          <div className="space-y-1.5">
            <div className="h-3.5 w-24 animate-pulse rounded bg-slate-800" />
            <div className="h-3 w-32 animate-pulse rounded bg-slate-800/70" />
          </div>
        </div>
        <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-slate-800" />
      </div>
      <div className="flex items-center justify-between border-t border-slate-800/60 pt-3">
        <div className="h-3 w-12 animate-pulse rounded bg-slate-800" />
        <div className="h-3 w-16 animate-pulse rounded bg-slate-800/60" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [healthState, setHealthState] = useState<HealthState>({ kind: "checking" });
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    async function poll(): Promise<void> {
      const now = new Date();
      try {
        const response = await fetch("/api/health", { cache: "no-store" });
        const data: unknown = await response.json();

        if (!isHealthResponse(data) || (response.status !== 200 && response.status !== 503)) {
          throw new Error("Unexpected health response shape from backend.");
        }

        if (isMountedRef.current) {
          setHealthState({ kind: "available", health: data, checkedAt: now });
        }
      } catch {
        if (isMountedRef.current) {
          setHealthState({ kind: "unavailable", checkedAt: now });
        }
      }
    }

    void poll();
    const intervalId = window.setInterval(() => void poll(), POLL_INTERVAL_MS);

    return () => {
      isMountedRef.current = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const overallStatus: "ok" | "degraded" | "unavailable" | "checking" =
    healthState.kind === "checking"
      ? "checking"
      : healthState.kind === "unavailable"
      ? "unavailable"
      : healthState.health.status;

  const isAvailable = healthState.kind === "available";

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 font-sans text-slate-100">
      {/* Ambient gradient blob */}
      <div
        className="pointer-events-none fixed inset-0 overflow-hidden"
        aria-hidden="true"
      >
        <div className="absolute -top-40 left-1/2 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-indigo-600/5 blur-3xl" />
        <div className="absolute bottom-0 right-0 h-[400px] w-[600px] rounded-full bg-violet-600/5 blur-3xl" />
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Header                                                              */}
      {/* ------------------------------------------------------------------ */}
      <header className="relative z-10 border-b border-slate-800/70 bg-slate-950/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold text-white shadow-lg shadow-indigo-500/20">
              K
            </div>
            <span className="text-base font-bold tracking-tight text-white">Kontexa</span>
          </div>
          <div className="flex items-center gap-3">
            {overallStatus === "ok" && (
              <StatusBadge status="ok" />
            )}
            {overallStatus === "degraded" && (
              <StatusBadge status="degraded" />
            )}
            {(overallStatus === "unavailable" || overallStatus === "checking") && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800/50 px-2.5 py-0.5 text-xs font-medium text-slate-400">
                <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400" />
                {overallStatus === "checking" ? "Checking…" : "Unreachable"}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Main                                                                */}
      {/* ------------------------------------------------------------------ */}
      <main className="relative z-10 mx-auto w-full max-w-5xl flex-1 px-6 py-12 sm:px-8">

        {/* Hero */}
        <div className="mb-12 space-y-3">
          <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-4xl font-extrabold tracking-tight text-transparent sm:text-5xl">
            System Status
          </h1>
          <p className="max-w-xl text-base leading-relaxed text-slate-400">
            Live readiness check for the Kontexa backend and its data store dependencies.
          </p>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Overall status banner                                            */}
        {/* ---------------------------------------------------------------- */}
        {healthState.kind === "available" && (
          <div
            className={`mb-8 flex flex-col gap-4 rounded-2xl border p-5 sm:flex-row sm:items-center sm:justify-between ${
              healthState.health.status === "ok"
                ? "border-emerald-500/20 bg-emerald-500/5"
                : "border-amber-500/20 bg-amber-500/5"
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-xl text-lg ${
                  healthState.health.status === "ok"
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "bg-amber-500/15 text-amber-400"
                }`}
              >
                {healthState.health.status === "ok" ? "✓" : "⚠"}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-200">
                  {healthState.health.status === "ok"
                    ? "All systems operational"
                    : "Partial outage detected"}
                </p>
                <p className="text-xs text-slate-500">
                  {healthState.health.service} v{healthState.health.version} ·{" "}
                  {healthState.health.environment}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Last checked</p>
              <p className="font-mono text-xs text-slate-400">
                {formatCheckedAt(healthState.checkedAt)}
              </p>
              <p className="mt-0.5 text-xs text-slate-600">
                Auto-refreshes every {POLL_INTERVAL_MS / 1000}s
              </p>
            </div>
          </div>
        )}

        {healthState.kind === "unavailable" && (
          <div className="mb-8 flex flex-col gap-4 rounded-2xl border border-red-500/20 bg-red-500/5 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-500/15 text-lg text-red-400">
                ✕
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-200">Backend unreachable</p>
                <p className="text-xs text-slate-500">
                  Could not contact the API. Is the backend running?
                </p>
              </div>
            </div>
            <p className="font-mono text-xs text-slate-500">
              {formatCheckedAt(healthState.checkedAt)}
            </p>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Service cards                                                    */}
        {/* ---------------------------------------------------------------- */}
        <section aria-label="Service health">
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Services
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {healthState.kind === "checking" &&
              SERVICES.map((s) => <SkeletonCard key={s.id} />)}

            {isAvailable &&
              SERVICES.map((service) => (
                <ServiceCard
                  key={service.id}
                  service={service}
                  health={healthState.health}
                />
              ))}

            {healthState.kind === "unavailable" &&
              SERVICES.map((s) => (
                <div
                  key={s.id}
                  className="flex flex-col gap-4 rounded-2xl border border-slate-800/50 bg-slate-900/40 p-5 opacity-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800/80 text-xl text-slate-600">
                      {s.icon}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-400">{s.label}</p>
                      <p className="text-xs text-slate-600">{s.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center border-t border-slate-800/60 pt-3">
                    <span className="text-xs text-slate-600">Unknown</span>
                  </div>
                </div>
              ))}
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Stack summary cards                                              */}
        {/* ---------------------------------------------------------------- */}
        <section aria-label="Technology stack" className="mt-10">
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Stack
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              {
                num: "01",
                color: "text-indigo-400",
                title: "Next.js & TypeScript",
                body: "React App Router, strict type checking, Tailwind CSS, ESLint.",
              },
              {
                num: "02",
                color: "text-violet-400",
                title: "FastAPI & Python 3.12+",
                body: "Modular monolith managed via uv, Ruff linting, Pytest coverage.",
              },
              {
                num: "03",
                color: "text-sky-400",
                title: "PostgreSQL + Redis",
                body: "pgvector extension for embeddings. Redis for cache and sessions.",
              },
            ].map(({ num, color, title, body }) => (
              <div
                key={num}
                className="space-y-2 rounded-2xl border border-slate-800/60 bg-slate-900/40 p-5 backdrop-blur-sm"
              >
                <div className={`font-mono text-xs font-semibold ${color}`}>{num}</div>
                <h3 className="text-sm font-bold text-slate-200">{title}</h3>
                <p className="text-xs leading-relaxed text-slate-500">{body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Footer                                                              */}
      {/* ------------------------------------------------------------------ */}
      <footer className="relative z-10 border-t border-slate-800/70 bg-slate-950/80 px-6 py-5 sm:px-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-3 text-xs text-slate-600 sm:flex-row">
          <span>Kontexa — Foundation initialized</span>
          <div className="flex gap-5 font-mono">
            <span>GET /health</span>
            <span>GET /api/v1/health</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
