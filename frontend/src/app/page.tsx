export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans flex flex-col justify-between p-8 sm:p-16">
      <header className="max-w-5xl mx-auto w-full flex justify-between items-center border-b border-slate-800 pb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
            K
          </div>
          <span className="text-xl font-bold tracking-tight text-white">Kontexa</span>
        </div>
        <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          Foundation Initialized
        </span>
      </header>

      <main className="max-w-5xl mx-auto w-full py-16 flex flex-col gap-12">
        <div className="space-y-4">
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            AI Workspace for Software Engineers
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl leading-relaxed">
            Kontexa engineering foundation baseline. Modular monolith architecture prepared for context retrieval, codebase indexing, and developer workflows.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-3">
            <div className="text-indigo-400 font-mono text-sm font-semibold">01. Frontend</div>
            <h3 className="text-lg font-bold text-slate-200">Next.js & TypeScript</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              React App Router, strict TypeScript typing, Tailwind CSS styling, and automated ESLint checks.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-3">
            <div className="text-purple-400 font-mono text-sm font-semibold">02. Backend</div>
            <h3 className="text-lg font-bold text-slate-200">FastAPI & Python 3.12+</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Modular monolith foundation managed via <code className="text-purple-300 font-mono">uv</code>, Ruff linting, and Pytest.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-3">
            <div className="text-emerald-400 font-mono text-sm font-semibold">03. Infrastructure</div>
            <h3 className="text-lg font-bold text-slate-200">Docker & Data Stores</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Containerized local development stack featuring PostgreSQL with <code className="text-emerald-300 font-mono">pgvector</code> and Redis.
            </p>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h4 className="text-sm font-semibold text-slate-300">Backend Health Endpoint</h4>
            <p className="text-xs text-slate-500 font-mono mt-1">GET /health</p>
          </div>
          <a
            href="http://localhost:8000/health"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-colors border border-slate-700"
          >
            http://localhost:8000/health
          </a>
        </div>
      </main>

      <footer className="max-w-5xl mx-auto w-full border-t border-slate-800 pt-6 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-500 gap-4">
        <div>Kontexa Core Repository Initialized</div>
        <div className="flex gap-6 font-mono">
          <span>Docs: /docs</span>
          <span>Rules: /docs/CODE_RULES.md</span>
        </div>
      </footer>
    </div>
  );
}
